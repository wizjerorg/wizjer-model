"""Training-time variants of messages (used by `build.py --augment`).

A variant keeps the label, the scam types and the wording, and changes what a detector must not
rely on: amounts, codes, dates, names, tracking numbers, diacritics and spacing. Both classes get
these changes, so that, for example, missing Polish letters never becomes a scam signal on its own.
Scam messages additionally get their links swapped for other real look-alike domains of the same
brand (data/pools/lookalikes.json, from CERT Polska's public list), sometimes a spoofed sender,
and sometimes Cyrillic look-alike letters in the brand name, as seen in real campaigns.

build.py makes variants only of training messages, after the split, so nothing leaks into
validation or test.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

POOLS = Path(__file__).resolve().parent.parent / "data" / "pools" / "lookalikes.json"

# Which brand a message imitates, judged from its text and sender.
BRAND_HINTS = {
    "inpost": r"inpost|paczkomat", "poczta": r"poczt|pocztex|awizo", "dpd": r"\bdpd\b", "dhl": r"\bdhl\b",
    "olx": r"\bolx\b", "allegro": r"allegro", "vinted": r"vinted", "otomoto": r"otomoto",
    "pko": r"\bi?pko\b|\biko\b", "mbank": r"mbank", "santander": r"santander", "pekao": r"pekao|peopay",
    "ing": r"\bing\b", "millennium": r"millen", "alior": r"alior", "bnp": r"\bbnp\b", "blik": r"\bblik",
    "revolut": r"revolut", "netflix": r"netflix|n\.e\.t", "orange": r"orange", "pge": r"\bpge\b",
    "etoll": r"e-?toll", "podatki": r"podat|urz[aą]d skarb|e-?urz[aą]d|\bpit\b|\bkas\b",
    "zus": r"\bzus\b", "nfz": r"\bnfz\b|e-?zdrowie|pacjent", "mandat": r"mandat|wykroczeni|gitd|grzywn",
    "parking": r"parking|parkow", "booking": r"booking|rezerwacj", "binance": r"binance",
    "gov": r"mobywatel|m-?obywatel|profil zaufany|gov|rz[aą]d",
}
BRAND_RES = {b: re.compile(p, re.I) for b, p in BRAND_HINTS.items()}

URL_RE = re.compile(r"(?<![@\w.])(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})(/[^\s\"'<>)]*)?", re.I)
AMOUNT_RE = re.compile(r"(?<![\d,.])(\d{1,3}(?:[  ]\d{3})+|\d+)(?:([,.])(\d{2}))?(\s?)(zł|zl|PLN|pln|EUR|€|USD|\$)")
DATE_RE = re.compile(r"(?<![\d.,/-])(\d{1,2})([./-])(\d{1,2})(?:\2(\d{4}|\d{2}))?(?![\d,.]|\s?(?:zł|zl|PLN|EUR))")
LONG_DIGITS_RE = re.compile(r"(?<![\w/.:=?&-])\d{10,30}(?![\w/-])")
CODE_RE = re.compile(r"(?<![\w/.,:=?&+-])\d{4,8}(?![\w/,:-]|\.\d)")
SPLIT_CODE_RE = re.compile(r"(?<![\w/])(\d{2,3})-(\d{3})(?![\w/])")

FEMALE = ["Anna", "Kasia", "Marta", "Ola", "Agnieszka", "Magda", "Ewa", "Joanna", "Natalia", "Monika", "Basia", "Zosia", "Ania", "Karolina", "Beata", "Iwona", "Edyta", "Lidia", "Maja", "Hanna"]
MALE = ["Piotr", "Tomasz", "Marek", "Paweł", "Krzysztof", "Michał", "Kuba", "Jan", "Adam", "Łukasz", "Bartek", "Mariusz", "Grzegorz", "Marcin", "Wojtek", "Andrzej", "Arkadiusz", "Janek", "Daniel", "Kamil"]
NAME_RE = re.compile(r"\b(" + "|".join(FEMALE + MALE) + r")\b")

DIACRITICS = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
HOMOGLYPHS = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "y": "у", "x": "х", "i": "і", "A": "А", "E": "Е", "O": "О", "P": "Р", "C": "С", "T": "Т", "K": "К", "M": "М", "H": "Н", "B": "В", "l": "I"}
BRAND_WORDS = re.compile(r"\b(InPost|INPOST|Inpost|Allegro|ALLEGRO|Orange|ORANGE|Netflix|NETFLIX|Poczta|OLX|Vinted|Santander|mBank|Pekao|BLIK|Blik|Revolut|mObywatel|PGE|DPD|DHL|ZUS|NFZ|Booking)\b")
SMS_SENDERS = ["Info", "Powiadomienie", "SMSINFO", "Weryfikacja", "Autoryzacja", "Kurier", "Dostawa", "Platnosci", "Alert"]


def load_pools(path: Path = POOLS) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    return {b: v for b, v in json.loads(path.read_text(encoding="utf-8"))["brands"].items() if v}


def brand_of(text: str, sender: str) -> str | None:
    hay = f"{sender} {text}"
    for brand, rx in BRAND_RES.items():
        if rx.search(hay):
            return brand
    return None


def random_digits(rng: random.Random, n: int) -> str:
    return str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(n - 1))


def fails_iban(digits: str) -> str:
    """Make sure a 26-digit number is not a valid Polish IBAN (nobody's real account)."""
    if len(digits) == 26 and int(digits[2:] + "2521" + digits[:2]) % 97 == 1:
        digits = digits[:-1] + str((int(digits[-1]) + 1) % 10)
    return digits


def vary_amounts(text: str, rng: random.Random) -> str:
    def repl(m: re.Match) -> str:
        whole = int(m.group(1).replace(" ", "").replace(" ", ""))
        new = max(1, round(whole * rng.uniform(0.4, 2.5))) if whole > 0 else rng.randint(1, 9)
        out = f"{new:,}".replace(",", " ") if re.search(r"[  ]", m.group(1)) else str(new)
        if m.group(2):
            out += m.group(2) + f"{rng.randint(0, 99):02d}"
        return out + m.group(4) + m.group(5)
    return AMOUNT_RE.sub(repl, text)


def vary_dates(text: str, rng: random.Random) -> str:
    def repl(m: re.Match) -> str:
        day, month = int(m.group(1)), int(m.group(3))
        if not (1 <= day <= 31 and 1 <= month <= 12):
            return m.group(0)
        d, mo = rng.randint(1, 28), rng.randint(1, 12)
        out = (f"{d:02d}" if len(m.group(1)) == 2 else str(d)) + m.group(2) + (f"{mo:02d}" if len(m.group(3)) == 2 else str(mo))
        if m.group(4):
            out += m.group(2) + m.group(4)
        return out
    return DATE_RE.sub(repl, text)


def vary_numbers(text: str, rng: random.Random) -> str:
    text = LONG_DIGITS_RE.sub(lambda m: fails_iban(random_digits(rng, len(m.group(0)))), text)
    text = SPLIT_CODE_RE.sub(lambda m: random_digits(rng, len(m.group(1))) + "-" + random_digits(rng, 3), text)

    def code(m: re.Match) -> str:
        s = m.group(0)
        if len(s) == 4 and s[:2] in {"19", "20"}:
            return s  # a year
        return random_digits(rng, len(s))
    return CODE_RE.sub(code, text)


def vary_names(text: str, rng: random.Random) -> str:
    return NAME_RE.sub(lambda m: rng.choice(FEMALE if m.group(1) in FEMALE else MALE), text)


def spacing_noise(text: str, rng: random.Random) -> str:
    if rng.random() < 0.5:
        text = re.sub(r"([.,!?]) (?=\w)", lambda m: m.group(1) if rng.random() < 0.3 else m.group(0), text)
    if rng.random() < 0.3:
        text = re.sub(r" (?=\w)", lambda m: "  " if rng.random() < 0.05 else " ", text)
    return text


SCAM_TLDS = ["top", "cfd", "icu", "sbs", "shop", "online", "site", "info", "xyz", "eu.cc", "live", "vip", "click", "lol", "cyou", "pl-info.top", "com"]
SHORTENERS = {"bit.ly", "t.co", "tinyurl.com", "cutt.ly", "is.gd", "tiny.cc", "e.vg", "urlz.fr", "v.ht", "rb.gy", "shorturl.at", "bit.do", "ln.run", "tt.vg", "vo.la", "did.li", "shrtn.sbs"}


def mutate_domain(host: str, rng: random.Random) -> str:
    """Another plausible scam domain of the same shape: new TLD, sometimes digits added."""
    labels = host.split(".")
    core = labels[0] if len(labels) == 2 else "-".join(labels[:-1])
    if rng.random() < 0.4:
        core += str(rng.randint(2, 999))
    return f"{core}.{rng.choice(SCAM_TLDS)}"


def random_path(rng: random.Random) -> str:
    return "/" + "".join(rng.choice("abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(rng.randint(4, 9)))


def swap_links(text: str, brand: str | None, pools: dict[str, list[str]], rng: random.Random) -> str:
    pool = pools.get(brand or "", [])

    def repl(m: re.Match) -> str:
        host = m.group(1).lower()
        if re.fullmatch(r"[\d.]+", host):
            return m.group(0)
        scheme = re.match(r"https?://", m.group(0), re.I)
        path = m.group(2) or ""
        if host in SHORTENERS:
            return (scheme.group(0) if scheme else "") + host + random_path(rng)
        new_host = rng.choice(pool) if pool and rng.random() < 0.7 else mutate_domain(host, rng)
        r = rng.random()
        if r < 0.3:
            path = ""
        elif r < 0.6:
            path = random_path(rng)
        return (scheme.group(0) if scheme else "") + new_host + path
    return URL_RE.sub(repl, text)


def homoglyphs(text: str, rng: random.Random) -> str:
    def repl(m: re.Match) -> str:
        word = list(m.group(0))
        spots = [i for i, ch in enumerate(word) if ch in HOMOGLYPHS]
        for i in rng.sample(spots, min(len(spots), rng.randint(1, 2))):
            word[i] = HOMOGLYPHS[word[i]]
        return "".join(word)
    return BRAND_WORDS.sub(repl, text, count=1)


def variant(text: str, sender: str, subject: str, label: str, source: str, rng: random.Random, pools: dict[str, list[str]]) -> tuple[str, str, str]:
    new_text, new_subject = text, subject
    if rng.random() < 0.7:
        new_text = vary_amounts(new_text, rng)
    if rng.random() < 0.6:
        new_text = vary_dates(new_text, rng)
    if rng.random() < 0.7:
        new_text, new_subject = vary_numbers(new_text, rng), vary_numbers(new_subject, rng)
    if rng.random() < 0.5:
        new_text = vary_names(new_text, rng)
    if rng.random() < 0.3:
        new_text, new_subject = new_text.translate(DIACRITICS), new_subject.translate(DIACRITICS)
    new_sender = sender
    if label == "scam":
        if rng.random() < 0.8:
            new_text = swap_links(new_text, brand_of(text, sender), pools, rng)
        if rng.random() < 0.15:
            new_text = homoglyphs(new_text, rng)
        if source == "sms" and rng.random() < 0.3:
            new_sender = rng.choice(SMS_SENDERS + [f"+48 {rng.choice('5678')}{rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}"])
    # Last, so that a "word.Word" it creates is never mistaken for a link above.
    new_text = spacing_noise(new_text, rng)
    return new_text, new_sender, new_subject


def make_variants(text: str, sender: str, subject: str, label: str, source: str, n: int, rng: random.Random, pools: dict[str, list[str]]) -> list[tuple[str, str, str]]:
    """Up to n distinct variants, each different from the original."""
    seen = {(text, sender, subject)}
    out = []
    for _ in range(n * 3):
        v = variant(text, sender, subject, label, source, rng, pools)
        if v not in seen:
            seen.add(v)
            out.append(v)
            if len(out) == n:
                break
    return out
