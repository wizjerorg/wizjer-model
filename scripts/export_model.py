"""Pack a model saved by train_baseline.py --save into one small file for the app.

    python scripts/train_baseline.py --save dist/model.json
    python scripts/export_model.py dist/model.json dist/wizjer-baseline.bin

File layout (little-endian): the 4 bytes "WZJ1", a uint32 header length, the header as UTF-8
JSON (dim, scale, bias, meta_weight, thresholds, golden), then `dim` int16 values: weight i is
value i × scale. (Signed bytes would halve the size but round most weights to zero.) Features are computed exactly as in train_baseline.features(); the golden
messages carry the scores this file gives them, for testing a port.

The export checks what rounding the weights to bytes costs: the largest change in a test score
and the AUC on the test split before and after.
"""

import argparse
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_baseline as tb  # noqa: E402


def quantize(weights: dict[int, float], dim: int) -> tuple[list[int], float]:
    scale = max(abs(v) for v in weights.values()) / 32767
    q = [0] * dim
    for i, v in weights.items():
        q[i] = round(v / scale)
    return q, scale


def dequantized(q: list[int], scale: float) -> list[float]:
    return [v * scale for v in q]


def score(w: list[float], bias: float, feats: dict[int, float]) -> float:
    return tb.sigmoid(bias + sum(w[i] * v for i, v in feats.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", type=Path, help="JSON written by train_baseline.py --save")
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    model = json.loads(args.model.read_text(encoding="utf-8"))
    dim = model["dim"]
    if dim != tb.DIM or model["meta_weight"] != tb.META_WEIGHT:
        print("the model was trained with other feature settings than train_baseline.py now has", file=sys.stderr)
        return 1
    weights = {int(k): v for k, v in model["weights"].items()}
    full = [0.0] * dim
    for i, v in weights.items():
        full[i] = v
    q, scale = quantize(weights, dim)
    small = dequantized(q, scale)

    test = tb.load("test")
    before, after, worst = [], [], 0.0
    for r in test:
        f = tb.features(r)
        a, b = score(full, model["bias"], f), score(small, model["bias"], f)
        before.append((a, r))
        after.append((b, r))
        worst = max(worst, abs(a - b))
    golden = [g | {"score": round(score(small, model["bias"], tb.features(g)), 6)} for g in model.get("golden", [])]

    header = {"format": "wizjer-baseline/1", "dim": dim, "scale": scale, "bias": model["bias"],
              "meta_weight": model["meta_weight"], "thresholds": model["thresholds"], "golden": golden}
    blob = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    args.out.write_bytes(b"WZJ1" + struct.pack("<I", len(blob)) + blob + struct.pack(f"<{dim}h", *q))

    zero = sum(1 for v in q if v == 0)
    print(f"wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB); {zero} of {dim} weights round to 0")
    print(f"test: largest score change {worst:.4f}; AUC {tb.auc(before):.4f} -> {tb.auc(after):.4f}")
    for lang_source in ("pl/sms", "pl/email", "pl/notification"):
        lang, source = lang_source.split("/")
        sub = lambda scored: [(s, r) for s, r in scored if r["lang"] == lang and r["source"] == source and r["origin"] in tb.OWN]
        if sub(before):
            print(f"  {lang_source} real: AUC {tb.auc(sub(before)):.4f} -> {tb.auc(sub(after)):.4f}")
    return 0 if not math.isnan(worst) else 1


if __name__ == "__main__":
    sys.exit(main())
