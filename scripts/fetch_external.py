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
import html
import io
import json
import random
import re
import sys
import tarfile
import time
import urllib.parse
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
        "lang": "pl",
    },
    "nkjp1m": {
        "url": "https://clip.ipipan.waw.pl/NationalCorpusOfPolish?action=AttachFile&do=get&target=NKJP-PodkorpusMilionowy-1.2.tar.gz",
        "file": "NKJP-PodkorpusMilionowy-1.2.tar.gz",
        "cite": "Przepiórkowski et al. (2012), National Corpus of Polish (NKJP), 1-million-word subcorpus v1.2, CC BY",
        "license": "CC-BY",
        "lang": "pl",
    },
    "tatoeba_uk": {
        "url": "https://downloads.tatoeba.org/exports/per_language/ukr/ukr_sentences.tsv.bz2",
        "file": "ukr_sentences.tsv.bz2",
        "cite": "Tatoeba (tatoeba.org), Ukrainian sentences, CC BY 2.0 FR",
        "license": "CC-BY-2.0-FR",
        "lang": "uk",
    },
    "wiki_pl_talk": {
        "url": "https://pl.wikipedia.org/w/api.php",
        "file": "user_talk_pages.jsonl",
        "cite": "Wikipedia contributors, Polish Wikipedia user talk pages, CC BY-SA 4.0",
        "license": "CC-BY-SA-4.0",
        "lang": "pl",
        "pages": 3000,
    },
}
DEFAULT = list(SOURCES)

BLANK_LINES_RE = re.compile(r"\n{3,}")


def download_wiki_talk(name: str, target: Path) -> None:
    """Random user talk pages through the MediaWiki API, 50 per request, one request a second."""
    spec = SOURCES[name]
    done = 0
    with target.open("w", encoding="utf-8", newline="\n") as out:
        while done < spec["pages"]:
            query = urllib.parse.urlencode({
                "action": "query", "format": "json", "formatversion": 2, "generator": "random",
                "grnnamespace": 3, "grnlimit": 50, "prop": "revisions", "rvprop": "content", "rvslots": "main",
            })
            request = urllib.request.Request(f"{spec['url']}?{query}", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response:
                pages = json.loads(response.read().decode("utf-8")).get("query", {}).get("pages", [])
            for page in pages:
                revisions = page.get("revisions") or [{}]
                content = revisions[0].get("slots", {}).get("main", {}).get("content", "")
                out.write(json.dumps({"title": page["title"], "content": content}, ensure_ascii=False) + "\n")
            done += len(pages)
            time.sleep(1)


def download(name: str) -> Path:
    spec = SOURCES[name]
    target = RAW / name / spec["file"]
    if target.exists():
        print(f"  {name}: already downloaded")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    if name == "wiki_pl_talk":
        print(f"  {name}: fetching {spec['pages']} random user talk pages")
        download_wiki_talk(name, target)
        return target
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


def convert_tatoeba(name: str, path: Path) -> list[dict]:
    """Everyday sentences, as short chat or SMS messages from people (all genuine)."""
    spec = SOURCES[name]
    rng = random.Random(7)
    out, seen = [], set()
    for line in bz2.decompress(path.read_bytes()).decode("utf-8").split("\n"):
        parts = line.split("\t")
        if len(parts) != 3 or len(parts[2]) < 8 or parts[2].casefold() in seen:
            continue
        seen.add(parts[2].casefold())
        rec = record(name, rng.choice(["sms", "notification"]), "legit", parts[2])
        rec.update(lang=spec["lang"], topic="conversation", license=spec["license"],
                   source_url=f"https://tatoeba.org/sentences/show/{parts[0]}")
        out.append(rec)
    return out


NKJP_TYPES = {"typ_konwers": "conversation", "typ_net_interakt": "internet", "typ_listy": "letters"}
NKJP_AB = re.compile(r'<ab\b[^>]*xml:id="([^"]+)"[^>]*>(.*?)</ab>', re.S)
NKJP_NOISE = re.compile(r"\((?:śmiech|niezrozumiałe|kaszel|szum|westchnienie|pauza)[^)]*\)|\[[^\]]*\]", re.I)


def convert_nkjp(path: Path) -> list[dict]:
    """Conversations and interactive internet texts (Usenet, forums, chats) from NKJP-1M.

    Each utterance or post becomes one genuine message: conversation turns as SMS or chat,
    short posts as chat, long posts as e-mail-like messages.
    """
    rng = random.Random(11)
    out, seen = [], set()
    # One pass over the compressed archive (random access into a .tar.gz re-reads it from the start).
    texts, kinds = {}, {}
    with tarfile.open(path, "r|gz") as tar:
        for member in tar:
            folder, _, file = member.name.strip("./").rpartition("/")
            if file == "header.xml":
                header = tar.extractfile(member).read().decode("utf-8", "replace")
                kinds[folder] = next((v for k, v in NKJP_TYPES.items() if f'#{k}"' in header), None)
            elif file == "text.xml":
                texts[folder] = tar.extractfile(member).read().decode("utf-8", "replace")
    for text_id in sorted(texts):
        kind = kinds.get(text_id)
        if kind:
            for ab_id, raw in NKJP_AB.findall(texts[text_id]):
                text = html.unescape(re.sub(r"<[^>]+>", "", raw))
                text = NKJP_NOISE.sub("", text).strip().lstrip("–-—").strip()
                text = re.sub(r"\s+", " ", text)
                if not 12 <= len(text) <= 800 or text.casefold() in seen:
                    continue
                seen.add(text.casefold())
                source = rng.choice(["sms", "notification"]) if kind == "conversation" else (
                    "email" if len(text) > 300 else "notification")
                rec = record("nkjp1m", source, "legit", text)
                rec.update(lang="pl", topic=kind, license=SOURCES["nkjp1m"]["license"],
                           source_url=f"https://clip.ipipan.waw.pl/NationalCorpusOfPolish#{text_id}/{ab_id}")
                out.append(rec)
    return out


SIGNATURE = re.compile(
    r"(\[\[(?:Wikipedysta|Wikipedystka|User|Użytkownik|Użytkowniczka|Dyskusja wikipedyst[ya]|Dyskusja wikipedystki|"
    r"User talk|Specjalna:Wkład)[^\]]*\]\][^\n]*?)?\d{1,2}:\d{2}, \d{1,2} \w+ \d{4} \((?:CET|CEST|UTC)\)", re.I)
WIKI_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
WIKI_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
WIKI_EXTERNAL = re.compile(r"\[(https?://\S+)(?: ([^\]]*))?\]")
WIKI_BOTS = re.compile(r"\bbot|witaj w wikipedii|witamy w wikipedii|poczekalni|zgłoszon[ya] do (usunięcia|poczekalni)|"
                       r"naruszenie praw autorskich|ostrzeżenie|zablokowan|integracja|nominacj", re.I)


# Wiki plumbing rather than a message: page names, encoded anchors, list markup, administrative notices.
WIKI_JUNK = re.compile(r"(Wikipedia|Wikipedysta|Kategoria|Szablon|Plik|Pomoc|Dyskusja)[ :]\S|\.C[0-9A-F]\.[0-9A-F]|\bSDU\b|^[;|!]|"
                       r"nazwa użytkownika jest niezgodna|twój artykuł nie nadaje się|brudnopis", re.I)


def wiki_message(chunk: str) -> str:
    text = SIGNATURE.sub("", chunk)
    for _ in range(3):
        text = WIKI_TEMPLATE.sub("", text)
    text = WIKI_EXTERNAL.sub(lambda m: f"{m.group(2) or ''} {m.group(1)}".strip(), text)
    text = WIKI_LINK.sub(r"\1", text)
    text = re.sub(r"<[^>]+>|'{2,}|^[:*#]+", "", text, flags=re.M)
    text = re.sub(r"\[\[(?:Plik|File|Kategoria|Grafika):[^\]]*\]\]", "", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip(" -–—")


def convert_wiki_talk(path: Path) -> list[dict]:
    """Messages people left each other on user talk pages: each signed comment is one message."""
    out, seen = [], set()
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        page = json.loads(line)
        for section in re.split(r"^==+[^=\n]*==+\s*$", page["content"], flags=re.M):
            for chunk in re.split(r"(?<=\((?:CET|UTC)\))|(?<=\(CEST\))", section):
                if not SIGNATURE.search(chunk):
                    continue
                text = wiki_message(chunk)
                if (not 15 <= len(text) <= 900 or len(text.split()) < 3 or WIKI_BOTS.search(text)
                        or WIKI_JUNK.search(text) or text.casefold() in seen):
                    continue
                seen.add(text.casefold())
                rec = record("wiki_pl_talk", "notification" if len(text) <= 300 else "email", "legit", text)
                title = page["title"].replace(" ", "_")
                rec.update(lang="pl", topic="conversation", license=SOURCES["wiki_pl_talk"]["license"],
                           source_url=f"https://pl.wikipedia.org/wiki/{urllib.parse.quote(title)}")
                out.append(rec)
    return out


def convert(name: str, path: Path) -> list[dict]:
    if name == "uci_sms":
        return convert_uci(path)
    if name == "nkjp1m":
        return convert_nkjp(path)
    if name == "wiki_pl_talk":
        return convert_wiki_talk(path)
    if name.startswith("tatoeba_"):
        return convert_tatoeba(name, path)
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
