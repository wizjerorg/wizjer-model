#!/usr/bin/env python3
"""Collect genuine Alert RCB messages from the government's public archive.

Alert RCB is the Polish government's emergency SMS (storms, floods, air threats, unsafe tap
water, siren tests). The archive at https://www.gov.pl/web/rcb/komunikaty quotes each alert.
They are real, legitimate SMS that sound urgent ("UWAGA!", "nie zbliżaj się", "śledź
komunikaty"), so they teach the model that urgency alone is not fraud.

Alerts are sent without Polish letters (SMS limit of 160 characters), so the archive's
quotes are stored without them, as phones show them. Repeated alerts with identical wording
are kept once. Output: data/real/pl/sms/legit/government_alerts.jsonl.

    python scripts/collect_rcb.py              # all pages
    python scripts/collect_rcb.py --pages 5    # newest 5 pages only

Standard library only.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "real" / "pl" / "sms" / "legit" / "government_alerts.jsonl"
BASE = "https://www.gov.pl"
LIST = BASE + "/web/rcb/komunikaty?page={page}&size=10"
USER_AGENT = "wizjer-model-collect/0.1 (+https://wizjer.org)"

DIACRITICS = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
HREF = re.compile(r'<div class="title">\s*<a href="(/web/rcb/[^"]+)"', re.S)
INTRO = re.compile(r'<div class="intro">(.*?)</div>', re.S)
DATE = re.compile(r'<span class="date">\s*(\d{2})\.(\d{2})\.(\d{4})')
QUOTE = re.compile(r"[„\"“”]([^„\"“”]{15,400})[\"”“]")


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", "replace")


def text_of(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def as_sms(quote: str) -> str:
    quote = unicodedata.normalize("NFC", quote).strip().strip(" .") + ("." if quote.strip().endswith(".") else "")
    return quote.translate(DIACRITICS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pages", type=int, default=0, help="how many archive pages to read (0 = all)")
    args = parser.parse_args()

    existing = OUT.read_text(encoding="utf-8").split("\n") if OUT.exists() else []
    seen = {json.loads(l)["text"].casefold() for l in existing if l.strip()}
    added = 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Each alert is written as soon as it is found, so stopping with Ctrl+C keeps the progress.
    with OUT.open("a", encoding="utf-8", newline="\n") as out:
        page = 1
        while True:
            try:
                body = fetch(LIST.format(page=page))
            except OSError as e:
                print(f"page {page}: {e}")
                break
            items = []
            for block in body.split("<li>")[1:]:
                href, intro, d = HREF.search(block), INTRO.search(block), DATE.search(block)
                if href and "alert" in href.group(1).lower():
                    items.append((href.group(1), text_of(intro.group(1)) if intro else "", d))
            if not items:
                break
            for href, text, d in items:
                m = QUOTE.search(text)
                if not m:
                    continue
                sms = as_sms(m.group(1))
                if sms.casefold() in seen:
                    continue
                seen.add(sms.casefold())
                out.write(json.dumps({
                    "sender": "Alert RCB",
                    "text": sms,
                    "source_url": BASE + href,
                    "date": f"{d.group(3)}-{d.group(2)}-{d.group(1)}" if d else "",
                    "edited": "Polish letters removed, as in the SMS",
                }, ensure_ascii=False) + "\n")
                out.flush()
                added += 1
            print(f"page {page}: {added} new so far", flush=True)
            page += 1
            if args.pages and page > args.pages:
                break
            time.sleep(0.5)
    print(f"added {added} alerts to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
