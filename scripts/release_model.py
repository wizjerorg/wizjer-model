"""Publish the exported model as a GitHub release, which the Wizjer app picks up on its own.

    python scripts/release_model.py [--tag model-2026.10.23] [--dry-run]

The release is tagged model-YYYY.MM.DD (the app compares these dates; add .2, .3 … for more
than one release a day) and carries:

    wizjer-baseline.bin   the model in the app's format (export_model.py)
    model.json            the full-precision model (train_baseline.py --save)
    BASELINE.md           the evaluation report

Needs the GitHub CLI (`gh`), logged in to an account that can publish to this repository.
--dry-run only writes dist/RELEASE_NOTES.md and prints the command.
"""

import argparse
import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
REPO = "wizjerorg/wizjer-model"
FILES = ("wizjer-baseline.bin", "model.json", "BASELINE.md")
# Test-table rows quoted in the notes: real Polish messages, overall and per channel.
ROWS = {"pl real": "All", "pl real sms": "SMS", "pl real email": "E-mail", "pl real notification": "Chat notifications"}


def notes() -> str:
    rows = {}
    for line in (DIST / "BASELINE.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # | subset | n | recall | FPR | precision | FP | FN | AUC | recall@1%FPR |
        if len(cells) == 9 and cells[0] in ROWS and cells[0] not in rows:
            rows[cells[0]] = cells
    table = "\n".join(
        f"| {ROWS[key]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[7]} |" for key, cells in rows.items()
    )
    return f"""The hashed n-gram logistic regression from `scripts/train_baseline.py`, trained on the data in this repository, open corpora and anonymised chat messages that aren't published (see the README).

The Wizjer app downloads `wizjer-baseline.bin` from the latest release by itself and switches to it once it has checked that the file reproduces its own test scores on the phone.

Real Polish test messages (never used in training), at the model's thresholds:

| Messages | Count | Scams caught | Genuine flagged | AUC |
|---|---:|---:|---:|---:|
{table}

Files: `wizjer-baseline.bin` (the app's format, 16-bit weights), `model.json` (full precision), `BASELINE.md` (the full evaluation).
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tag", default="model-" + datetime.date.today().strftime("%Y.%m.%d"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not re.fullmatch(r"model-\d+(\.\d+)*", args.tag):
        print(f"the tag must look like model-2026.10.23, not {args.tag}", file=sys.stderr)
        return 1
    missing = [name for name in FILES if not (DIST / name).is_file()]
    if missing:
        print(f"missing in dist/: {', '.join(missing)} (train with --save and export first)", file=sys.stderr)
        return 1

    notes_file = DIST / "RELEASE_NOTES.md"
    notes_file.write_text(notes(), encoding="utf-8")
    command = ["gh", "release", "create", args.tag, *(str(DIST / name) for name in FILES),
               "--repo", REPO, "--title", "Model " + args.tag.removeprefix("model-"), "--notes-file", str(notes_file)]
    print(" ".join(command))
    if args.dry_run:
        print(f"(dry run; notes in {notes_file})")
        return 0
    if shutil.which("gh") is None:
        print("gh isn't installed: install the GitHub CLI and run `gh auth login`, or create the release on github.com", file=sys.stderr)
        return 1
    return subprocess.run(command).returncode


if __name__ == "__main__":
    sys.exit(main())
