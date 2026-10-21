#!/usr/bin/env python3
"""Build data/pools/lookalikes.json: real look-alike domains per impersonated brand.

Takes CERT Polska's public list of dangerous domains (https://hole.cert.pl/domains/v2/domains.txt),
keeps the ones that imitate a known brand and samples up to --per-brand of each. The augmentation
step in build.py uses them to put real-world scam links into variants of scam messages.

    python scripts/make_pools.py

Standard library only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "pools" / "lookalikes.json"
SOURCE = "https://hole.cert.pl/domains/v2/domains.txt"
USER_AGENT = "wizjer-model-pools/0.1 (+https://wizjer.org)"

# Brand -> pattern over the domain name. Kept narrow on purpose: a loose pattern ("pit") would
# pull in unrelated domains ("capital", "hospital").
BRANDS = {
    "inpost": r"inpost|inp0st|lnpost|paczkomat",
    "poczta": r"poczt|pocztex|e-?awizo",
    "dpd": r"(^|[.-])dpd(?!ns)",
    "dhl": r"(^|[.-])dhl",
    "olx": r"olx",
    "allegro": r"allegro|a11egro|allegr0",
    "vinted": r"vinted",
    "otomoto": r"otomoto",
    "pko": r"(^|[.-])i?pko|(^|[.-])iko[.-]",
    "mbank": r"mbank",
    "santander": r"santander",
    "pekao": r"pekao|peopay",
    "ing": r"(^|[.-])ing[.-]|moje-?ing",
    "millennium": r"millen+i",
    "alior": r"alior",
    "bnp": r"(^|[.-])bnp",
    "blik": r"blik",
    "revolut": r"revolut",
    "netflix": r"netfl|netfi|nflx",
    "orange": r"orange",
    "play": r"play24|(^|[.-])play-?pl",
    "pge": r"(^|[.-])(gk)?pge",
    "tauron": r"tauron",
    "energa": r"energa",
    "etoll": r"e-?toll",
    "gov": r"gov-?pl|govpl|pl-?gov|m-?obywatel|profil-?zaufany",
    "podatki": r"podat|e-?urzad|urzad-?skarb",
    "zus": r"(^|[.-])zus",
    "nfz": r"(^|[.-])nfz|e-?zdrowie|pacjent",
    "mandat": r"(^|[.-])mandat|cepik|gitd|canard",
    "parking": r"parking|parkow",
    "booking": r"booking|bookng",
    "binance": r"binance",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--per-brand", type=int, default=150)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    request = urllib.request.Request(SOURCE, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        domains = sorted({d.strip().lower() for d in response.read().decode("utf-8", "replace").split("\n") if d.strip()})
    print(f"{len(domains)} domains on the list")

    rng = random.Random(args.seed)
    pools = {}
    for brand, pattern in BRANDS.items():
        rx = re.compile(pattern)
        hits = [d for d in domains if rx.search(d)]
        pools[brand] = sorted(rng.sample(hits, min(len(hits), args.per_brand)))
        print(f"  {brand:10} {len(hits):6} -> {len(pools[brand])}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": SOURCE,
        "note": "Domains from CERT Polska's public warning list, grouped by the brand they imitate.",
        "date": dt.date.today().isoformat(),
        "brands": pools,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
