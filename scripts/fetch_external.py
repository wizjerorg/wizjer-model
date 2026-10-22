#!/usr/bin/env python3
"""Download the optional third-party datasets and convert them to the Wizjer schema.

Files are saved to external/raw/ and converted to external/converted/<name>.jsonl. Neither
folder is committed: these datasets keep their own licences (CC BY 4.0, Tatoeba CC BY 2.0 FR)
and must be cited.
Afterwards run `python scripts/build.py --include-external`.

    python scripts/fetch_external.py                       # default selection
    python scripts/fetch_external.py --sources uci_sms nazario
    python scripts/fetch_external.py --max-per-source 5000 # cap large e-mail corpora

Standard library only.
"""

from __future__ import annotations

import argparse
import bz2
import csv
import io
import json
import random
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "external" / "raw"
CONVERTED = ROOT / "external" / "converted"
USER_AGENT = "wizjer-model-fetch/0.1 (+https://wizjer.org)"
ZENODO = "https://zenodo.org/records/8339691/files/{}?download=1"
CC_BY = "CC-BY-4.0"


SOURCES = {
    "uci_sms": {
        "url": "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip",
        "file": "sms_spam_collection.zip",
        "cite": "Almeida & Hidalgo (2011), SMS Spam Collection, UCI, doi:10.24432/C5CC84",
    },
    "mendeley_smishing": {
        "url": "https://data.mendeley.com/public-files/datasets/f45bkkt8pr/files/edb361de-918d-469f-9106-e84823830665/file_downloaded",
        "file": "Dataset_5971.zip",
        "cite": "Mishra & Soni (2022), SMS Phishing Dataset, Mendeley Data, doi:10.17632/f45bkkt8pr.1",
    },
    "nazario": {
        "url": ZENODO.format("Nazario.csv"),
        "file": "Nazario.csv",
        "cite": "Champa, Rabbi & Zibran (2024), Phishing Email Curated Datasets, doi:10.5281/zenodo.8339691",
    },
    "nigerian_fraud": {
        "url": ZENODO.format("Nigerian_Fraud.csv"),
        "file": "Nigerian_Fraud.csv",
        "cite": "Champa, Rabbi & Zibran (2024), Phishing Email Curated Datasets, doi:10.5281/zenodo.8339691",
    },
    "spamassassin": {
        "url": ZENODO.format("SpamAssasin.csv"),
        "file": "SpamAssasin.csv",
        "cite": "Champa, Rabbi & Zibran (2024), Phishing Email Curated Datasets, doi:10.5281/zenodo.8339691",
    },
    "ceas08": {
        "url": ZENODO.format("CEAS_08.csv"),
        "file": "CEAS_08.csv",
        "cite": "Champa, Rabbi & Zibran (2024), Phishing Email Curated Datasets, doi:10.5281/zenodo.8339691",
    },
    "enron": {
        "url": ZENODO.format("Enron.csv"),
        "file": "Enron.csv",
        "cite": "Champa, Rabbi & Zibran (2024), Phishing Email Curated Datasets, doi:10.5281/zenodo.8339691",
    },
    "tatoeba_pl": {
        "url": "https://downloads.tatoeba.org/exports/per_language/pol/pol_sentences.tsv.bz2",
        "file": "pol_sentences.tsv.bz2",
        "cite": "Tatoeba (tatoeba.org), Polish sentences, CC BY 2.0 FR",
        "license": "CC-BY-2.0-FR",
    },
}
DEFAULT = list(SOURCES)

BLANK_LINES_RE = re.compile(r"\n{3,}")


def download(name: str) -> Path:
    spec = SOURCES[name]
    target = RAW / name / spec["file"]
    if target.exists():
        print(f"  {name}: already downloaded")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"  {name}: downloading {spec['url']}")
    request = urllib.request.Request(spec["url"], headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    target.write_bytes(data)
    print(f"  {name}: {len(data) / 1e6:.1f} MB")
    return target


def record(name: str, source: str, label: str, text: str, sender: str = "", subject: str = "") -> dict:
    return {
        "lang": "en", "source": source, "label": label, "types": [], "topic": "",
        "sender": sender.strip()[:200], "subject": subject.strip()[:300],
        "text": BLANK_LINES_RE.sub("\n\n", text.replace("\r\n", "\n")).strip(),
        "origin": f"external:{name}", "license": CC_BY,
    }


def convert_uci(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as z:
        raw = z.read("SMSSpamCollection").decode("utf-8", errors="replace")
    out = []
    for line in raw.splitlines():
        tag, _, text = line.partition("\t")
        if text:
            # Its spam is mostly premium-rate "you've won" scams, but not all of it is fraud.
            out.append(record("uci_sms", "sms", "legit" if tag == "ham" else "spam", text))
    return out


def convert_mendeley(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        raw = z.read(name).decode("utf-8", errors="replace")
    out = []
    for row in csv.DictReader(io.StringIO(raw)):
        row = {k.strip().lower(): (v or "") for k, v in row.items() if k}
        label = row.get("label", "").strip().lower()
        text = row.get("text", "")
        if not text:
            continue
        mapped = {"ham": "legit", "smishing": "scam", "spam": "spam"}.get(label)
        if mapped:
            out.append(record("mendeley_smishing", "sms", mapped, text))
    return out


def convert_emails(name: str, path: Path, positive: str) -> list[dict]:
    """Zenodo CSVs: label 1 = phishing/spam, 0 = legitimate. `positive` is our label for 1."""
    csv.field_size_limit(sys.maxsize if sys.maxsize < 2**31 else 2**31 - 1)
    out = []
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            body = row.get("body") or ""
            if not body.strip():
                continue
            label = positive if str(row.get("label", "")).strip() == "1" else "legit"
            out.append(record(name, "email", label, body[:6000], row.get("sender", ""), row.get("subject", "")))
    return out


def convert_tatoeba(path: Path) -> list[dict]:
    """Everyday Polish sentences, as short chat or SMS messages from people (all genuine)."""
    rng = random.Random(7)
    out, seen = [], set()
    for line in bz2.decompress(path.read_bytes()).decode("utf-8").split("\n"):
        parts = line.split("\t")
        if len(parts) != 3 or len(parts[2]) < 8 or parts[2].casefold() in seen:
            continue
        seen.add(parts[2].casefold())
        rec = record("tatoeba_pl", rng.choice(["sms", "notification"]), "legit", parts[2])
        rec.update(lang="pl", topic="conversation", license=SOURCES["tatoeba_pl"]["license"],
                   source_url=f"https://tatoeba.org/sentences/show/{parts[0]}")
        out.append(rec)
    return out


def convert(name: str, path: Path) -> list[dict]:
    if name == "uci_sms":
        return convert_uci(path)
    if name == "tatoeba_pl":
        return convert_tatoeba(path)
    if name == "mendeley_smishing":
        return convert_mendeley(path)
    # Nazario and Nigerian fraud are fraud by definition; the others mix fraud with plain spam.
    positive = "scam" if name in {"nazario", "nigerian_fraud"} else "spam"
    return convert_emails(name, path, positive)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sources", nargs="+", choices=sorted(SOURCES), default=DEFAULT)
    parser.add_argument("--max-per-source", type=int, default=6000, help="random sample cap per dataset (0 = all)")
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    CONVERTED.mkdir(parents=True, exist_ok=True)
    for name in args.sources:
        print(f"{name} — {SOURCES[name]['cite']}")
        try:
            records = convert(name, download(name))
        except Exception as e:  # noqa: BLE001 - report and continue with the other sources
            print(f"  {name}: failed ({e})", file=sys.stderr)
            continue
        if args.max_per_source and len(records) > args.max_per_source:
            records = random.Random(args.seed).sample(records, args.max_per_source)
        with (CONVERTED / f"{name}.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            for rec in records:
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        labels = {label: sum(r["label"] == label for r in records) for label in ("scam", "spam", "legit")}
        print(f"  {name}: {len(records)} records {labels}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
