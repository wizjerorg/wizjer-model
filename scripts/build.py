#!/usr/bin/env python3
"""Validate, de-duplicate and split the Wizjer scam dataset.

Reads every <lang>/<source>/<label>/<category>.jsonl file under data/examples (messages written
for the project) and data/real (real messages quoted in public sources, each with its
`source_url`), fills in the fields implied by the path, checks each record, rejects exact
duplicates, groups near-duplicates (and records sharing a `campaign`) so that variants of one
message never land in different splits, and writes dist/{train,validation,test}.jsonl and
dist/STATS.md.

The test split is built from real messages only, so that it measures how the model does on
what people actually receive, not on our own writing.

    python scripts/build.py                     # build dist/
    python scripts/build.py --check             # validate only
    python scripts/build.py --include-external  # also add external/converted/*.jsonl
    python scripts/build.py --augment 4         # add up to 4 variants of each real training message

Standard library only.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import augment  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "data" / "examples"
REAL = ROOT / "data" / "real"
EXTERNAL = ROOT / "external" / "converted"
DIST = ROOT / "dist"

LANGS = {"pl", "uk", "en"}
SOURCES = {"sms", "notification", "email"}
LABELS = {"scam", "legit"}
EXTERNAL_LABELS = LABELS | {"spam"}  # third-party "spam" that isn't necessarily fraud
SCAM_TYPES = {
    "parcel_fee", "bank", "code_theft", "family", "marketplace", "investment", "job", "utility",
    "government", "prize", "remote_access", "phishing", "gambling", "extortion", "fake_shop", "loan",
}
FIELDS = {"text", "sender", "subject", "app", "types", "hard", "campaign", "note"}
OWN = {"real", "written"}  # origins kept in this repository (not third-party)
REAL_FIELDS = FIELDS | {"source_url", "date", "edited"}
MAX_LEN = {"sms": 1200, "notification": 1500, "email": 6000}
SPLITS = ("train", "validation", "test")
NEAR_DUPLICATE = 0.6  # Jaccard similarity of character 4-grams
LICENSE = "MIT"

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
URLISH_RE = re.compile(r"\S*[./@]\S*")
IBAN_RE = re.compile(r"(?<![\dA-Z])(?:PL ?)?(\d{2}(?: ?\d{4}){6})(?!\d)")
DIGITS_RE = re.compile(r"\d")
SPACES_RE = re.compile(r"\s+")


@dataclass
class Record:
    lang: str
    source: str
    label: str
    category: str
    text: str
    where: str
    sender: str = ""
    subject: str = ""
    app: str = ""
    types: list[str] = field(default_factory=list)
    hard: bool = False
    campaign: str = ""
    origin: str = "written"
    license: str = LICENSE
    source_url: str = ""
    id: str = ""
    split: str = ""

    def output(self) -> dict:
        return {
            "id": self.id,
            "lang": self.lang,
            "source": self.source,
            "label": self.label,
            "types": self.types,
            "topic": self.category if self.label != "scam" else "",
            "sender": self.sender,
            "subject": self.subject,
            "app": self.app,
            "text": self.text,
            "hard": self.hard,
            "origin": self.origin,
            "source_url": self.source_url,
            "license": self.license,
            "split": self.split,
        }


class Problems:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")

    def warn(self, where: str, message: str) -> None:
        self.warnings.append(f"{where}: {message}")


def normalize(text: str) -> str:
    return SPACES_RE.sub(" ", unicodedata.normalize("NFKC", text)).strip().casefold()


def stable_id(*parts: str) -> str:
    return hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:12]


def is_cyrillic(c: str) -> bool:
    return "CYRILLIC" in unicodedata.name(c, "")


def cyrillic_share(text: str) -> float | None:
    """Share of Cyrillic among letters, ignoring links, e-mail addresses and domains.

    Words that mix scripts are left out: Cyrillic look-alikes inside Latin words ("zalеgle")
    are a scammer's trick to dodge filters, not a sign of the message's language.
    """
    letters: list[str] = []
    for word in URLISH_RE.sub(" ", text).split():
        alpha = [c for c in word if c.isalpha()]
        if len({is_cyrillic(c) for c in alpha}) == 1:
            letters += alpha
    if len(letters) < 12:
        return None
    return sum(map(is_cyrillic, letters)) / len(letters)


def passes_iban_checksum(digits: str) -> bool:
    """True if a 26-digit Polish account number would be a valid IBAN (PL = 25 21)."""
    return int(digits[2:] + "2521" + digits[:2]) % 97 == 1


def check_record(rec: Record, problems: Problems) -> None:
    where = rec.where
    if not rec.text.strip():
        problems.error(where, "empty text")
    if len(rec.text) > MAX_LEN[rec.source]:
        problems.error(where, f"text longer than {MAX_LEN[rec.source]} characters")
    if rec.text != rec.text.strip():
        problems.warn(where, "leading or trailing whitespace")
    if rec.source == "email" and (not rec.subject or not rec.sender):
        problems.error(where, "e-mails need `sender` and `subject`")
    if rec.source == "notification" and (not rec.app or not rec.sender):
        problems.error(where, "notifications need `app` and `sender`")
    if rec.label == "scam":
        unknown = [t for t in rec.types if t not in SCAM_TYPES]
        if unknown:
            problems.error(where, f"unknown scam types {unknown}")
        if not rec.types:
            problems.error(where, "scam without a type")
    elif rec.types:
        problems.error(where, "`types` is only for scams")

    share = cyrillic_share(f"{rec.subject} {rec.text}")
    if share is not None:
        if rec.lang == "uk" and share < 0.5:
            problems.error(where, f"lang is uk but only {share:.0%} of letters are Cyrillic")
        if rec.lang in {"pl", "en"} and share > 0.1:
            problems.error(where, f"lang is {rec.lang} but {share:.0%} of letters are Cyrillic")

    for match in IBAN_RE.finditer(f"{rec.subject} {rec.text}"):
        digits = match.group(1).replace(" ", "")
        if passes_iban_checksum(digits):
            problems.error(where, f"account number {match.group(1)} passes the IBAN checksum; make it fictional")


def read_examples(problems: Problems, root: Path = EXAMPLES, origin: str = "written") -> list[Record]:
    """Read data/real (origin "real") or data/examples ("written")."""
    records: list[Record] = []
    real = origin == "real"
    allowed = REAL_FIELDS if real else FIELDS
    for path in sorted(root.rglob("*.jsonl")) if root.exists() else []:
        rel = path.relative_to(root)
        if len(rel.parts) != 4:
            problems.error(str(rel), "expected <lang>/<source>/<label>/<category>.jsonl")
            continue
        lang, source, label, filename = rel.parts
        category = filename.removesuffix(".jsonl")
        if lang not in LANGS or source not in SOURCES or label not in LABELS or not NAME_RE.match(category):
            problems.error(str(rel), "bad path (see data/README.md)")
            continue
        if label == "scam" and category not in SCAM_TYPES:
            problems.error(str(rel), f"`{category}` is not a scam type")
            continue

        for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            where = f"{root.name}/{rel.as_posix()}:{number}"
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                problems.error(where, f"invalid JSON ({e.msg})")
                continue
            if not isinstance(obj, dict) or not isinstance(obj.get("text"), str):
                problems.error(where, "each line must be an object with a `text` string")
                continue
            extra = set(obj) - allowed
            if extra:
                problems.error(where, f"unknown fields {sorted(extra)}")
            if real and not str(obj.get("source_url", "")).startswith("https://"):
                problems.error(where, "real messages need a `source_url`")
            types = obj.get("types", [category] if label == "scam" else [])
            if not isinstance(types, list):
                problems.error(where, "`types` must be a list")
                types = []
            rec = Record(
                lang=lang, source=source, label=label, category=category, where=where,
                text=obj["text"], sender=str(obj.get("sender", "")), subject=str(obj.get("subject", "")),
                app=str(obj.get("app", "")), types=list(dict.fromkeys(types)), hard=bool(obj.get("hard", False)),
                campaign=str(obj.get("campaign", "")),
                origin=origin,
                source_url=str(obj.get("source_url", "")),
            )
            if label == "scam" and category not in rec.types:
                rec.types.insert(0, category)
            check_record(rec, problems)
            rec.id = stable_id(lang, source, rec.sender, rec.subject, rec.text)
            records.append(rec)
    return records


def read_external(problems: Problems) -> list[Record]:
    records: list[Record] = []
    for path in sorted(EXTERNAL.glob("*.jsonl")):
        # Split on "\n" only: texts may contain U+2028 and friends, which splitlines() breaks on.
        for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            if not line.strip():
                continue
            obj = json.loads(line)
            where = f"external/{path.name}:{number}"
            if obj.get("lang") not in LANGS or obj.get("source") not in SOURCES or obj.get("label") not in EXTERNAL_LABELS:
                problems.error(where, "bad lang/source/label")
                continue
            text = str(obj.get("text", "")).strip()
            if not text:
                continue
            rec = Record(
                lang=obj["lang"], source=obj["source"], label=obj["label"], category=obj.get("topic", "") or "external",
                text=text[: MAX_LEN[obj["source"]]], where=where, sender=obj.get("sender", ""),
                subject=obj.get("subject", ""), types=obj.get("types", []), origin=obj["origin"], license=obj["license"],
            )
            rec.id = stable_id(rec.lang, rec.source, rec.sender, rec.subject, rec.text)
            records.append(rec)
    return records


def drop_duplicates(records: list[Record], problems: Problems) -> list[Record]:
    seen: dict[tuple, Record] = {}
    kept: list[Record] = []
    for rec in records:
        key = (rec.lang, rec.source, normalize(rec.subject), normalize(rec.text))
        first = seen.get(key)
        if first is None:
            seen[key] = rec
            kept.append(rec)
        elif rec.origin in OWN and first.origin == rec.origin:
            problems.error(rec.where, f"duplicate of {first.where}")
        # A written example identical to a real one, and duplicates involving third-party data,
        # are simply dropped (the first copy, read in that order, wins).
    return kept


def template(text: str) -> str:
    """Text with digits and links neutralised, so variants of one template compare as equal."""
    return DIGITS_RE.sub("0", URLISH_RE.sub("url", normalize(text)))


def shingles(text: str, n: int = 4) -> set[str]:
    t = template(text)
    return {t[i : i + n] for i in range(max(1, len(t) - n + 1))}


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def assign_splits(records: list[Record], seed: int) -> None:
    """Group-wise split per category; near-duplicates and campaigns stay together.

    Real messages: 40% test, 10% validation, 50% train. Written examples: 90% train,
    10% validation, never test. A group that mixes both follows its real members, except that
    written members of a test group are left out (split "").
    """
    written = [r for r in records if r.origin in OWN]
    uf = UnionFind(len(written))

    buckets: dict[tuple, list[int]] = defaultdict(list)
    for i, rec in enumerate(written):
        buckets[(rec.lang, rec.source, rec.label, rec.category)].append(i)
    for members in buckets.values():
        grams = [shingles(written[i].subject + " " + written[i].text) for i in members]
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                inter = len(grams[a] & grams[b])
                if inter and inter / len(grams[a] | grams[b]) >= NEAR_DUPLICATE:
                    uf.union(members[a], members[b])

    by_campaign: dict[tuple, int] = {}
    for i, rec in enumerate(written):
        if rec.campaign:
            key = (rec.lang, rec.campaign)
            if key in by_campaign:
                uf.union(by_campaign[key], i)
            else:
                by_campaign[key] = i

    # Variants of a real message written by us (e.g. same campaign) join its group across categories.
    clusters: dict[int, list[int]] = defaultdict(list)
    for i in range(len(written)):
        clusters[uf.find(i)].append(i)
    home: dict[tuple, list[int]] = defaultdict(list)
    for root, members in clusters.items():
        rec = written[members[0]]
        has_real = any(written[i].origin == "real" for i in members)
        home[("real" if has_real else "written", rec.lang, rec.source, rec.label, rec.category)].append(root)

    shares = {"real": (0.4, 0.1), "written": (0.0, 0.1)}  # (test, validation)
    rng = random.Random(seed)
    for key in sorted(home):
        roots = sorted(home[key], key=lambda r: written[r].id)
        rng.shuffle(roots)
        n = len(roots)
        test_share, val_share = shares[key[0]]
        n_test = round(n * test_share) or (1 if test_share and n >= 2 else 0)
        n_val = round(n * val_share) or (1 if n >= 8 else 0)
        for position, root in enumerate(roots):
            split = "test" if position < n_test else "validation" if position < n_test + n_val else "train"
            for i in clusters[root]:
                # Test stays real-only. A written near-copy of a real test message can't go to
                # train either (it would leak), so it is left out of the build.
                written[i].split = "" if split == "test" and written[i].origin != "real" else split

    for rec in records:
        if rec.origin not in OWN:
            bucket = int(rec.id, 16) % 10
            rec.split = "test" if bucket == 0 else "validation" if bucket == 1 else "train"


def augmented(records: list[Record], n: int, seed: int) -> list[Record]:
    """Variants of training messages: n per real or legit message, n // 2 (at least 1) per written scam.

    Legit messages get the full count because there are fewer of them, and a detector learns
    false alarms from a thin legit class faster than it misses scams.
    """
    pools = augment.load_pools()
    rng = random.Random(seed)
    seen = {(r.lang, r.source, normalize(r.subject), normalize(r.text)) for r in records}
    out: list[Record] = []
    for rec in records:
        if rec.split != "train" or rec.origin not in OWN:
            continue
        count = n if rec.origin == "real" or rec.label == "legit" else max(1, n // 2)
        for text, sender, subject in augment.make_variants(rec.text, rec.sender, rec.subject, rec.label, rec.source, count, rng, pools):
            key = (rec.lang, rec.source, normalize(subject), normalize(text))
            if key in seen:
                continue
            seen.add(key)
            variant = dataclasses.replace(rec, text=text, sender=sender, subject=subject, origin="augmented", where=f"{rec.where} (variant)")
            variant.id = stable_id(variant.lang, variant.source, variant.sender, variant.subject, variant.text)
            out.append(variant)
    return out


def stats_markdown(records: list[Record]) -> str:
    lines = ["# Dataset statistics", "", "Generated by `scripts/build.py`.", ""]

    lines += ["## Messages", "", "| Language | Source | Scam | Legit | Spam* | Total |", "|---|---|---:|---:|---:|---:|"]
    table = Counter((r.lang, r.source, r.label) for r in records)
    for lang in sorted(LANGS):
        for source in sorted(SOURCES):
            row = [table[(lang, source, label)] for label in ("scam", "legit", "spam")]
            if sum(row):
                lines.append(f"| {lang} | {source} | {row[0]} | {row[1]} | {row[2]} | {sum(row)} |")
    totals = Counter(r.label for r in records)
    lines.append(f"| **all** | | **{totals['scam']}** | **{totals['legit']}** | **{totals['spam']}** | **{len(records)}** |")
    lines += ["", "\\* third-party spam that isn't necessarily fraud (only with `--include-external`).", ""]

    lines += ["## Scam types", "", "| Type | pl | uk | en | Total |", "|---|---:|---:|---:|---:|"]
    by_type = Counter((t, r.lang) for r in records if r.label == "scam" for t in r.types)
    for t in sorted(SCAM_TYPES, key=lambda t: -sum(by_type[(t, l)] for l in LANGS)):
        row = [by_type[(t, l)] for l in ("pl", "uk", "en")]
        lines.append(f"| {t} | {row[0]} | {row[1]} | {row[2]} | {sum(row)} |")

    lines += ["", "## Legit topics", "", "| Topic | pl | uk | en | Total |", "|---|---:|---:|---:|---:|"]
    by_topic = Counter((r.category, r.lang) for r in records if r.label == "legit" and r.origin in OWN)
    for topic in sorted({t for t, _ in by_topic}, key=lambda t: -sum(by_topic[(t, l)] for l in LANGS)):
        row = [by_topic[(topic, l)] for l in ("pl", "uk", "en")]
        lines.append(f"| {topic} | {row[0]} | {row[1]} | {row[2]} | {sum(row)} |")

    lines += ["", "## Splits", "", "| Split | Scam | Legit | Spam | Hard | Total |", "|---|---:|---:|---:|---:|---:|"]
    for split in SPLITS:
        part = [r for r in records if r.split == split]
        c = Counter(r.label for r in part)
        lines.append(f"| {split} | {c['scam']} | {c['legit']} | {c['spam']} | {sum(r.hard for r in part)} | {len(part)} |")

    lines += ["", "## Origin", "", "| Origin | Scam | Legit | Spam | Total |", "|---|---:|---:|---:|---:|"]
    for origin in sorted({r.origin for r in records}):
        c = Counter(r.label for r in records if r.origin == origin)
        lines.append(f"| {origin} | {c['scam']} | {c['legit']} | {c['spam']} | {sum(c.values())} |")
    lines += ["", "The test split contains real messages only (plus 10% of external corpora); augmented variants are train-only."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="validate only, write nothing")
    parser.add_argument("--include-external", action="store_true", help="add external/converted/*.jsonl")
    parser.add_argument("--augment", type=int, default=0, metavar="N", help="variants per real or legit training message (written scams get N // 2)")
    parser.add_argument("--seed", type=int, default=13, help="seed for the split assignment")
    args = parser.parse_args()

    problems = Problems()
    # Real messages first, so that a written example identical to one of them is dropped.
    records = read_examples(problems, REAL, "real") + read_examples(problems)
    if args.include_external:
        if not EXTERNAL.exists():
            print("external/converted/ is missing; run scripts/fetch_external.py first", file=sys.stderr)
            return 1
        records += read_external(problems)
    records = drop_duplicates(records, problems)

    for message in problems.warnings:
        print(f"warning: {message}", file=sys.stderr)
    for message in problems.errors:
        print(f"error: {message}", file=sys.stderr)
    origins = Counter("external" if r.origin.startswith("external") else r.origin for r in records)
    print(f"{origins['real']} real, {origins['written']} written, {origins['external']} external messages; "
          f"{len(problems.errors)} errors, {len(problems.warnings)} warnings")
    if problems.errors:
        return 1
    if args.check:
        return 0

    assign_splits(records, args.seed)
    left_out = sum(not r.split for r in records)
    records = [r for r in records if r.split]
    if left_out:
        print(f"left out {left_out} written messages that are near-copies of real test messages")
    if args.augment:
        records += augmented(records, args.augment, args.seed)
    DIST.mkdir(exist_ok=True)
    for split in SPLITS:
        with (DIST / f"{split}.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            for rec in sorted((r for r in records if r.split == split), key=lambda r: r.id):
                out.write(json.dumps(rec.output(), ensure_ascii=False) + "\n")
    (DIST / "STATS.md").write_text(stats_markdown(records), encoding="utf-8", newline="\n")
    counts = Counter(r.split for r in records)
    print("wrote dist/: " + ", ".join(f"{s} {counts[s]}" for s in SPLITS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
