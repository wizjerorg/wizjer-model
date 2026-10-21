#!/usr/bin/env python3
"""Collect genuine municipal messages from the public SISMS / BLISKO feed.

Polish towns send residents SMS and app notices through SISMS: water and power cuts, tax and
waste-fee reminders, weather warnings, events. They are real, legitimate messages that often
look like scams (deadlines, payments, links), which is exactly what the model must not flag.
The public page https://rejestracja.sisms.pl/wiadomosci shows only the newest 20, so this
script polls it politely and keeps every new one.

New messages are appended to data/real/pl/notification/legit/government.jsonl. Signature lines
that are just a person's name are removed; officials' roles stay.

    python scripts/collect_sisms.py                 # fetch once
    python scripts/collect_sisms.py --hours 24      # poll for a day (every 10 minutes)
    python scripts/collect_sisms.py --import rows.jsonl   # add rows saved by an earlier poll

Standard library only.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "real" / "pl" / "notification" / "legit" / "government.jsonl"
FEED = "https://rejestracja.sisms.pl/messages/getList"
PAGE = "https://rejestracja.sisms.pl/wiadomosci"
USER_AGENT = "wizjer-model-collect/0.1 (+https://wizjer.org)"
MAX_LEN = 1500

UPPER, LOWER = "A-ZĄĆĘŁŃÓŚŹŻ", "a-ząćęłńóśźż"
NAME = rf"[{UPPER}][{LOWER}]+(?:-[{UPPER}][{LOWER}]+)?"
# A signature line that is just a name ("Jan Kowalski", "mgr inż. Jan Kowalski").
NAME_LINE = re.compile(rf"^\s*(?:(?:dr|mgr|inż\.|prof\.)\s+)*{NAME}\s+{NAME}\s*$")


def clean(fragment: str) -> str:
    text = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    lines = [line.strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def parse(page: str) -> list[dict]:
    rows = []
    for block in page.split('class="single-message-wrapper"')[1:]:
        def grab(pattern: str) -> str:
            m = re.search(pattern, block, re.S)
            return clean(m.group(1)) if m else ""
        rows.append({
            "date": grab(r'<p class="message-data">(.*?)</p>'),
            "sender": grab(r"<h2>(.*?)</h2>"),
            "kind": grab(r'<span class="info">(.*?)</span>'),
            "text": grab(r"<article>(.*?)</article>"),
        })
    return rows


def to_record(row: dict) -> dict | None:
    text, edited = row["text"], []
    if not text or not row["sender"]:
        return None
    without_names = "\n".join(line for line in text.split("\n") if not NAME_LINE.match(line)).strip()
    if without_names != text:
        text, edited = without_names, ["personal names in the signature removed"]
    if len(text) > MAX_LEN:
        text = text[: text.rfind(" ", 0, MAX_LEN - 1)] + "…"
        edited.append("shortened")
    d, m, y = (row["date"].split(".") + ["", "", ""])[:3]
    record = {"app": "BLISKO", "sender": row["sender"], "text": text, "source_url": PAGE, "date": f"{y}-{m}-{d}" if y else ""}
    if edited:
        record["edited"] = "; ".join(edited)
    return record


def add(rows: list[dict]) -> int:
    existing = OUT.read_text(encoding="utf-8").split("\n") if OUT.exists() else []
    seen = {(json.loads(l)["sender"], json.loads(l)["text"]) for l in existing if l.strip()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    added = 0
    with OUT.open("a", encoding="utf-8", newline="\n") as out:
        for row in rows:
            rec = to_record(row)
            if rec and (rec["sender"], rec["text"]) not in seen:
                seen.add((rec["sender"], rec["text"]))
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                added += 1
    return added


def fetch() -> list[dict]:
    request = urllib.request.Request(FEED, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return parse(response.read().decode("utf-8", "replace"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hours", type=float, default=0, help="keep polling this long (0 = fetch once)")
    parser.add_argument("--interval", type=int, default=600, help="seconds between polls (min 300)")
    parser.add_argument("--import", dest="import_file", type=Path, help="add rows from a JSONL file instead of fetching")
    args = parser.parse_args()

    if args.import_file:
        rows = [json.loads(l) for l in args.import_file.read_text(encoding="utf-8-sig").split("\n") if l.strip()]
        print(f"added {add(rows)} of {len(rows)}")
        return 0
    end = time.time() + args.hours * 3600
    while True:
        try:
            print(f"{time.strftime('%H:%M')} added {add(fetch())}", flush=True)
        except OSError as e:
            print(f"{time.strftime('%H:%M')} error: {e}", flush=True)
        if time.time() >= end:
            return 0
        time.sleep(max(300, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
