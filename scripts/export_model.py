"""Pack a model saved by train_baseline.py --save into one small file for the app.

    python scripts/train_baseline.py --save dist/model.json
    python scripts/export_model.py dist/model.json dist/wizjer-baseline.bin

File layout, little-endian, chosen so the app can read it without a JSON library:

    "WZJ2"
    u32 dim, f64 scale, f64 bias, f64 meta_weight
    u16 n, then n × (str key, f64 threshold, f64 caution threshold)   key: "pl" or "pl/sms"
    u16 g, then g × (str lang, str source, str sender, str subject, str text, f64 score)
    dim × i16 weights                                                  weight i = value i × scale

where str is a u32 byte length and UTF-8 bytes. The thresholds flag at most 1% of genuine
messages; the caution thresholds, a softer "be careful" level, at most 5%. Features are computed
exactly as in train_baseline.features(); the g "golden" test messages carry the scores this file
gives them, for checking a port. (Signed bytes would halve the size but round most weights to 0.)

The export checks what rounding the weights costs: the largest change in a test score and the
AUC on the test split before and after.
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


# Made-up messages that exercise every branch of features() (sender addresses, mojibake, emoji,
# Cyrillic, shorteners, amounts…), added to the golden set so a port is checked on all of them.
PARITY = [
    {"lang": "pl", "source": "email", "sender": "PKO BP <bezpieczenstwo@pkobp-weryfikacja.com>", "subject": "Pilne: zweryfikuj dane",
     "text": "Szanowny Kliencie,\nTwoje konto zostanie zablokowane w ciągu 24h. Zaloguj się: https://www.pkobp-weryfikacja.com/login?id=7"},
    {"lang": "pl", "source": "email", "sender": "Allegro <allegro.pomoc@gmail.com>", "subject": "Faktura VAT 07/2026",
     "text": "W załączniku faktura. Hasło do pliku: 4821. Plik: faktura_07.zip"},
    {"lang": "pl", "source": "email", "sender": "mObywatel <powiadomienia@mobywatel.gov.pl>", "subject": "Nowy dokument",
     "text": "W aplikacji mObywatel czeka nowy dokument. Sprawdź: https://www.mobywatel.gov.pl"},
    {"lang": "pl", "source": "sms", "sender": "+48 512 304 991", "subject": "",
     "text": "CzeĹ›Ä‡ mamo, to mĂłj nowy numer 😊 napisz na WhatsApp"},
    {"lang": "pl", "source": "sms", "sender": "InPost", "subject": "",
     "text": "InPost: dopłata 1,99 zł do przesyłki. Opłać: bit.ly/3xQz9 lub inpost-pl.top/p/88 teraz"},
    {"lang": "pl", "source": "notification", "sender": "Ania", "subject": "",
     "text": "Hej! ❤️❤️ Wyślesz mi kod BLIK na 500 zł? Oddam jutro, przysięgam 🙏 KOD: 123456"},
    {"lang": "uk", "source": "sms", "sender": "Нова пошта", "subject": "",
     "text": "Ваша посилка затримана. Терміново сплатіть 29 грн: novaposhta-ua.top/pay 🚚"},
    {"lang": "uk", "source": "notification", "sender": "Олена", "subject": "",
     "text": "Привіт, мені прийшов код на твій номер, скинь мені 6 цифр будь ласка. Дякую! Pоlska"},
    {"lang": "en", "source": "sms", "sender": "", "subject": "",
     "text": "Your Netflix account is on hold. Update payment: https://netflix-billing.click/u?x=1 Reply STOP"},
    {"lang": "pl", "source": "sms", "sender": "Binance", "subject": "",
     "text": "Wykryto logowanie z Brazylii. Jeśli to nie Ty, zadzwoń +48 22 307 41 86 REF: BX1. Kwota 1 200,00 PLN, kod 77-210."},
    {"lang": "pl", "source": "notification", "sender": "", "subject": "",
     "text": "ŻÓŁĆ   ĘĄŚ — ΣΟΦΟΣ ﬁnał №5 ①②③ www.Example.pl/Ścieżka)."},
    {"lang": "pl", "source": "sms", "sender": "", "subject": "", "text": "ok"},
]


def score(w: list[float], bias: float, feats: dict[int, float]) -> float:
    return tb.sigmoid(bias + sum(w[i] * v for i, v in feats.items()))


def text(value: str) -> bytes:
    data = value.encode("utf-8")
    return struct.pack("<I", len(data)) + data


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

    strict, caution = model["thresholds"], model.get("thresholds_caution", {})
    out = b"WZJ2" + struct.pack("<Iddd", dim, scale, model["bias"], model["meta_weight"])
    out += struct.pack("<H", len(strict))
    for key, value in strict.items():
        out += text(key) + struct.pack("<dd", value, caution.get(key, value))
    golden = model.get("golden", []) + PARITY
    out += struct.pack("<H", len(golden))
    for g in golden:
        out += b"".join(text(g[k] or "") for k in ("lang", "source", "sender", "subject", "text"))
        out += struct.pack("<d", score(small, model["bias"], tb.features(g)))
    args.out.write_bytes(out + struct.pack(f"<{dim}h", *q))

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
