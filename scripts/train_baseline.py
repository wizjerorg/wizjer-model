#!/usr/bin/env python3
"""Train and evaluate a simple baseline scam classifier on dist/.

Logistic regression over hashed character and word n-grams plus a few message features
(links, numbers, sender). It is small, fast and easy to reason about: a yardstick for any
bigger model, and a tool for finding where the data is weak.

A decision threshold per language is chosen so that at most --max-fpr of genuine messages are
flagged (for Polish, of our own messages rather than the Tatoeba sentences). By default it rests on
out-of-fold scores from grouped cross-validation over train + validation, so it uses every
genuine message we have instead of the few in validation; the final model then trains on train +
validation. dist/BASELINE.md reports test results per language and channel, on real messages only,
and lists the worst mistakes (on test and on the held-out folds).

    python scripts/build.py --include-external --augment 4
    python scripts/train_baseline.py

Standard library only. Third-party "spam" (not necessarily fraud) is left out of training and
evaluation.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import itertools
import json
import math
import random
import re
import sys
import time
import unicodedata
from array import array
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
DIM = 1 << 20
OWN = {"real", "written"}

URL = re.compile(r"(?:https?://|www\.)\S+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:pl|com|net|org|info|top|site|online|eu|cc|xyz|me|ly|co|link|shop|live|cfd|icu|sbs|buzz|vip|help|biz|in|run|io|app|click|pro|club|life|one|sv|to|tk|ru|de|uk|us|lol|cyou|store)\b\S*", re.I)
SHORTENER = re.compile(r"\b(bit\.ly|t\.co|tinyurl|cutt\.ly|is\.gd|tiny\.cc|e\.vg|urlz\.fr|v\.ht|rb\.gy|shorturl\.at|bit\.do|ln\.run|tt\.vg|vo\.la|did\.li|goo\.su|tiny\.one|rebrand\.ly|wa\.me|t\.me|tiny\.pl|s\.id|cli\.co|x\.gd|u\.to|t\.ly|short\.gy|goo\.gl)\b", re.I)
# Brands that scams impersonate, and the domains their genuine links use.
BRANDS = {
    r"inpost|paczkomat": ("inpost.pl",), r"\bolx\b": ("olx.pl",), r"allegro": ("allegro.pl",), r"vinted": ("vinted.pl", "vinted.com"),
    r"otomoto": ("otomoto.pl",), r"\bdpd\b": ("dpd.com.pl", "dpd.pl"), r"\bdhl\b": ("dhl.com", "dhl.com.pl", "dhl24.com.pl"),
    r"poczta polska|pocztex": ("poczta-polska.pl", "pocztex.pl", "envelo.pl"), r"\bpko\b|ipko|\biko\b": ("pkobp.pl", "ipko.pl"),
    r"mbank": ("mbank.pl",), r"\bing\b": ("ing.pl",), r"pekao": ("pekao.com.pl",), r"santander|erste": ("santander.pl", "erste.pl"),
    r"millennium": ("bankmillennium.pl",), r"alior": ("aliorbank.pl",), r"\bblik\b": ("blik.com",),
    r"mobywatel|gov\.pl|profil zaufany|urzad skarbowy|ministerstw|\bzus\b|\bkas\b": ("gov.pl", "zus.pl", "podatki.gov.pl", "mobywatel.gov.pl"),
    r"\bpge\b": ("pge.pl", "gkpge.pl"), r"tauron": ("tauron.pl",), r"energa": ("energa.pl",), r"\benea\b": ("enea.pl",),
    r"orange": ("orange.pl",), r"\bplay\b": ("play.pl",), r"\bplus\b": ("plus.pl",), r"t-mobile": ("t-mobile.pl",),
    r"netflix": ("netflix.com",), r"facebook|messenger": ("facebook.com", "fb.com"), r"whatsapp": ("whatsapp.com", "wa.me"),
    r"bnp paribas": ("bnpparibas.pl",), r"credit agricole": ("credit-agricole.pl",), r"velobank": ("velobank.pl",),
    r"revolut": ("revolut.com",), r"binance": ("binance.com",), r"zondacrypto|zonda": ("zondacrypto.com",),
    r"booking": ("booking.com",), r"e-?toll": ("etoll.gov.pl",), r"\bnfz\b|pacjent\.gov": ("nfz.gov.pl", "pacjent.gov.pl"),
    r"apple|icloud": ("apple.com", "icloud.com"), r"microsoft|outlook|office 365": ("microsoft.com", "live.com", "office.com", "outlook.com"),
    r"paypal": ("paypal.com",), r"\bups\b": ("ups.com",), r"\bgls\b": ("gls-group.eu", "gls-pl.com"), r"fedex": ("fedex.com",),
    r"orlen": ("orlen.pl",), r"\bpzu\b": ("pzu.pl",), r"steam": ("steampowered.com", "steamcommunity.com"),
    r"privatbank|приватбанк": ("privatbank.ua",), r"monobank": ("monobank.ua",), r"nova poshta|нова пошта": ("novaposhta.ua",),
    r"ukrposhta|укрпошта": ("ukrposhta.ua",), r"\bdiia\b|(додат|застосун|портал)\w* «?дія": ("diia.gov.ua",),
    r"ощадбанк|oschadbank": ("oschadbank.ua",),
}
SENDER_ADDRESS = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
FREEMAIL = {"gmail.com", "wp.pl", "o2.pl", "onet.pl", "op.pl", "interia.pl", "interia.eu", "poczta.fm", "gazeta.pl", "tlen.pl",
            "outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com", "ukr.net", "i.ua", "meta.ua"}
META_WEIGHT = 0.3
# Cues scams combine (on lower-case text without Polish letters; each is Polish, then Ukrainian).
# Alone they are common in genuine messages too; the model learns how much each is worth, and
# especially their combinations with a link.
CUES = {
    "urgent": re.compile(r"\bpilne|natychmiast|niezwlocznie|w ciagu (24|48|12|2) ?(h|godz)|ostatni[ae]? (szans|wezwan|przypomn)|do godziny|dzisiaj do|termin (uplywa|mija)|"
                         r"терміново|негайно|протягом (24|48|12|2|однієї|доби)|останн\w* (попереджен|нагадуван|шанс)|сьогодні до"),
    "threat": re.compile(r"zablokowan|zawieszon|zostanie (zablok|zawiesz|usunie|anulow|wylacz|odlacz)|komornik|egzekuc|sad\b|do sadu|policj|prokurat|odlaczeni|utraci|"
                         r"заблоков|призупин|буде (заблок|видал|скасов|відключ|закрит)|арешт|виконавч|суд\b|судов|поліці|прокурат|кримінальн|відключен|втрат(ите|ити)|штраф"),
    "pay": re.compile(r"doplat|zaplac|oplac|uregul|wplac|przelej|platnos|naleznos|zaleglos|kwot[aey] \d|"
                      r"оплат|сплат|доплат|переказ|заборгован|борг|передоплат|внес(іть|ти)|переведіть"),
    "credentials": re.compile(r"zaloguj|zweryfikuj|weryfikac|potwierdz (swoje )?dane|zaktualizuj (swoje )?dane|haslo|dane karty|numer karty|kod (blik|sms|weryfik|autoryz)|"
                              r"podaj (mi )?(kod|ten kod|haslo)|przepisz (mi )?(go|kod)|(wyslij|przeslij|podeslij) (mi )?(kod|blik|ten kod)|potwierdz kodem|"
                              r"увійд|увійти|підтверд\w* (дані|акаунт|особ|картк|свій)|верифікац|пароль|дані (вашої )?картки|номер картки|cvv|термін дії картки|"
                              r"код (з|із) (смс|sms)|код підтвердж|баланс картки|скинь\w* (мені )?(код|цифр)|перешл\w* (мені )?(його|код)|повідом\w* код"),
    "elsewhere": re.compile(r"whatsapp|telegram|napisz do mnie|nowy numer|odpisz|odpowiedz (tak|na ten)|zadzwon (pod|na) |"
                            r"телеграм|вайбер|ватсап|вотсап|напиш(іть|и) (мені|у|в) |новий номер|пишу з (номера|чужого)|зателефонуй"),
    "prize": re.compile(r"wygral|wygrana|nagrod|gratul|bonus|darmow|prezent|zwrot (podatku|srodkow|pieniedzy)|odbierz|"
                        r"виграл|виграш|розіграш|подарун|безкоштовн|бонус|вітаємо|отримайте|компенсаці|виплат\w* (допомог|компенсац|грош)|грошов\w* допомог"),
    # Malware e-mails: an attachment to open, often a password-protected archive or a script file.
    "attachment": re.compile(r"w zalacz|zalacz(ony|ona|one|nik)|pobierz (plik|dokument|fakture)|haslo do (pliku|zalacznika|archiwum|faktury|otwarcia)|"
                             r"у вкладенн|вкладенн|завантаж\w* (файл|документ)|пароль до (файлу|архів)|"
                             r"\.(zip|rar|7z|exe|js|vbs|docm|xlsm|iso|img|hta|scr|jar|apk)\b"),
    # Fake bank security staff: "if it wasn't you, call…", case numbers, "safe account".
    "callback": re.compile(r"(jesli|jezeli|gdy) (to )?nie (ty|byl|ja|zlecal|dokonal|autoryzow)|nie (zlecal|autoryzowal|rozpoznaj)|zadzwon (natychmiast|pilnie|niezwlocznie|teraz)|oddzwon|"
                           r"\bref[:. #]|opiekun\w* sprawy|n(r|umer) sprawy|(dzial|wydzial|departament)\w* bezpieczenstwa|podejrzan\w* (aktywnos|transakc|logowa|operac|prob)|"
                           r"wykryto (logowanie|probe|podejrz|nowe urzadz)|nie rozlaczaj|konsultant\w* (oddzwoni|zadzwoni|skontaktuje)|bezpieczn\w* (rachun|kont)|"
                           r"якщо це (були )?не ви|служб\w* безпеки|підозріл\w* (операц|транзакц|вхід|активн|спроб)|спроб\w* входу|очікуйте (на )?дзвінк|зателефонує|"
                           r"співробітник\w* (банку|служби)|безпечн\w* рахун|не кладіть слухавку"),
    # "Someone posted your (edited) photos" lures and sextortion.
    "exposure": re.compile(r"(twoje|twoich|twoimi|twojego) (przerobion\w* |prywatne |nagie |intymne )?(zdjec|fotk|fotek|nagran|filmik)|przer[oa]bi\w* (zdjec|fotk|twoje)|nagie|intymn|"
                           r"kompromit|nagral\w* (cie|ciebie)|wrzucil\w* (twoje|tw)|"
                           r"ваші (інтимн\w* |приватн\w* )?(фото|відео|світлин)|інтимн|компромат"),
}
ACTIVE_CUES = set(CUES)
CYRILLIC = re.compile(r"[Ͱ-ϿЀ-ӿ]")
LATIN = re.compile(r"[a-ząćęłńóśźż]", re.I)
AMOUNT = re.compile(r"\d+(?:[.,]\d{2})?\s?(?:zł|zl|pln|eur|€|usd|\$)", re.I)
CODE = re.compile(r"(?<!\d)\d{4,8}(?!\d)")
PHONE = re.compile(r"(?:\+?48)?[ -]?\d{3}[ -]?\d{3}[ -]?\d{3}\b")
DIACRITICS = str.maketrans("ąćęłńóśźż", "acelnoszz")


MOJIBAKE = re.compile(r"[ĹÄĂÅÃâ][\x80-˿‐-›]")


def fix_mojibake(text: str) -> str:
    """Repair UTF-8 text shown in a single-byte code page ("CzeĹ›Ä‡" -> "Cześć"), word by word."""
    if not MOJIBAKE.search(text):
        return text
    out = []
    for word in text.split(" "):
        fixed = word
        if MOJIBAKE.search(word):
            for codec in ("cp1250", "cp1252", "latin-1"):
                try:
                    fixed = word.encode(codec).decode("utf-8")
                    break
                except (UnicodeEncodeError, UnicodeDecodeError):
                    continue
        out.append(fixed)
    return " ".join(out)


def norm(text: str) -> str:
    return unicodedata.normalize("NFKC", fix_mojibake(text)).lower()


def hashed(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "little") % DIM


def features(rec: dict) -> dict[int, float]:
    text = norm(rec["text"])
    plain = text.translate(DIACRITICS)
    feats: Counter = Counter()
    # Character n-grams on text without Polish letters (so their absence isn't a signal).
    padded = f" {re.sub(r'\s+', ' ', plain)} "
    for n in (3, 4, 5):
        for i in range(len(padded) - n + 1):
            feats["c" + padded[i:i + n]] += 1
    words = re.findall(r"\w+", plain)
    for w in words:
        feats["w" + w] += 1
    for a, b in zip(words, words[1:]):
        feats["b" + a + "_" + b] += 1
    if rec.get("subject"):
        for w in re.findall(r"\w+", norm(rec["subject"]).translate(DIACRITICS)):
            feats["s" + w] += 1
    hosts = [re.sub(r"^(?:https?://)?(?:www\.)?", "", u).split("/")[0].rstrip(".,:;!?)") for u in URL.findall(text)]
    for host in hosts:
        feats["url"] += 1
        feats["tld." + host.rsplit(".", 1)[-1]] += 1
        feats["host.parts." + str(min(host.count("."), 4))] += 1
        if "-" in host:
            feats["host.hyphen"] += 1
        if any(c.isdigit() for c in host):
            feats["host.digit"] += 1
    feats["amount"] += len(AMOUNT.findall(text))
    feats["code"] += len(CODE.findall(text))
    feats["phone"] += len(PHONE.findall(text))
    feats[f"source.{rec['source']}"] += 1
    feats[f"len.{min(len(text) // 40, 10)}"] += 1
    sender = rec.get("sender", "")
    # The strongest tells stay outside the length normalisation so long texts don't drown them.
    meta: Counter = Counter()
    if sender:
        kind = "num" if re.fullmatch(r"[+\d\s-]{7,}", sender) else "name"
        feats["sender." + kind] += 1
        # What an e-mail address says, never whether there is one (our genuine e-mails often lack it).
        address = SENDER_ADDRESS.search(sender.lower())
        if address:
            domain = address.group(1)
            feats["sender.tld." + domain.rsplit(".", 1)[-1]] += 1
            if domain in FREEMAIL:
                feats["sender.freemail"] += 1
            if "-" in domain:
                feats["sender.hyphen"] += 1
            if any(c.isdigit() for c in domain):
                feats["sender.digit"] += 1
            display = norm(sender[: address.start()]).translate(DIACRITICS)
            claimed = [d for pattern, domains in BRANDS.items() if re.search(pattern, display) for d in domains]
            if claimed:
                own = any(domain == d or domain.endswith("." + d) for d in claimed)
                meta["sender.brand.own" if own else "sender.brand.other"] += 1
    official = [d for pattern, domains in BRANDS.items() if re.search(pattern, plain) for d in domains]
    if official and hosts:
        # A brand named in the text with a link elsewhere is the classic phishing tell.
        own = all(any(h == d or h.endswith("." + d) for d in official) for h in hosts)
        meta["brand.link.own" if own else "brand.link.other"] += 1
    meta["mixed.script"] += sum(1 for w in text.split() if CYRILLIC.search(w) and LATIN.search(w))
    meta["shortener"] += len(SHORTENER.findall(text))
    cues = sorted(name for name, pattern in CUES.items() if name in ACTIVE_CUES and pattern.search(plain))
    for name in cues:
        feats["cue." + name] += 1
        if hosts:
            feats["cue.link." + name] += 1
    for a, b in itertools.combinations(cues, 2):
        feats[f"cue.{a}+{b}"] += 1
    feats[f"cue.count.{min(len(cues), 4)}"] += 1

    def hashed_counts(counts: Counter) -> dict[int, float]:
        out: dict[int, float] = {}
        for k, v in counts.items():
            if v > 0:
                h = hashed(k)
                out[h] = out.get(h, 0.0) + (1.0 + math.log(v))
        return out

    out = hashed_counts(feats)
    scale = 1.0 / math.sqrt(sum(x * x for x in out.values()) or 1.0)
    out = {k: v * scale for k, v in out.items()}
    for k, v in hashed_counts(meta).items():
        out[k] = out.get(k, 0.0) + META_WEIGHT * v
    return out


def load(split: str) -> list[dict]:
    rows = []
    for line in (DIST / f"{split}.jsonl").read_text(encoding="utf-8").split("\n"):
        if line.strip():
            r = json.loads(line)
            if r["label"] in ("scam", "legit"):
                rows.append(r)
    return rows


def sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z)) if z > -35 else 0.0


Features = tuple[array, array]


def featurize(rows: list[dict]) -> list[Features]:
    """Features of every row, computed once (as packed index and value arrays: a fifth of the memory of tuples)."""
    out = []
    for r in rows:
        f = features(r)
        out.append((array("I", f), array("d", f.values())))
    return out


def train(rows: list[dict], feats: list[Features], epochs: int, lr: float, l2: float, seed: int) -> tuple[list[float], float]:
    # Balance each (language, label, own or third-party) group to the same total weight.
    def group(r: dict) -> tuple:
        return r["lang"], r["label"], r["origin"] != "augmented" and r["origin"] not in OWN

    groups = Counter(group(r) for r in rows)
    weights = [len(rows) / (len(groups) * groups[group(r)]) for r in rows]
    data = [(f, 1.0 if r["label"] == "scam" else 0.0, w) for r, f, w in zip(rows, feats, weights)]
    w = [0.0] * DIM
    bias = 0.0
    rng = random.Random(seed)
    for epoch in range(epochs):
        rng.shuffle(data)
        step = lr / (1 + epoch)
        for (idx, val), y, weight in data:
            z = bias + sum(w[i] * v for i, v in zip(idx, val))
            g = (sigmoid(z) - y) * weight
            for i, v in zip(idx, val):
                w[i] -= step * (g * v + l2 * w[i])
            bias -= step * g
    return w, bias


def score(w: list[float], bias: float, f: Features) -> float:
    return sigmoid(bias + sum(w[i] * v for i, v in zip(*f)))


def fold_of(rec: dict, k: int) -> int:
    """Cross-validation fold by build group, so near-duplicates and their variants stay together."""
    key = rec.get("group") or rec["id"]
    return int.from_bytes(hashlib.blake2b(key.encode(), digest_size=4).digest(), "little") % k


MIN_LEGIT = 50  # genuine messages needed before a language or channel gets a threshold of its own


def pick_thresholds(scored: list[tuple[float, dict]], max_fpr: float) -> dict[str, float]:
    """Flag at most max_fpr of the genuine messages scored, per language ("pl") and, where there are
    enough genuine messages, per language and channel ("pl/email"); our own messages where we have
    enough of them, otherwise every genuine message of that language."""
    def cut(scores: list[float]) -> float:
        pool = sorted(scores, reverse=True)
        return max(pool[min(int(len(pool) * max_fpr), len(pool) - 1)] + 1e-9, 0.05)

    out = {}
    for lang in sorted({r["lang"] for _, r in scored}):
        legit = [(s, r) for s, r in scored if r["label"] == "legit" and r["lang"] == lang]
        own_only = sum(r["origin"] in OWN for _, r in legit) >= MIN_LEGIT
        pool = [(s, r) for s, r in legit if r["origin"] in OWN or not own_only]
        out[lang] = cut([s for s, _ in pool]) if pool else 0.5
        for source in sorted({r["source"] for _, r in pool}):
            sub = [s for s, r in pool if r["source"] == source]
            if len(sub) >= MIN_LEGIT:
                out[f"{lang}/{source}"] = cut(sub)
    return out


def threshold(t: dict[str, float], r: dict) -> float:
    return t.get(f"{r['lang']}/{r['source']}", t[r["lang"]])


def metrics(scored: list[tuple[float, dict]], t: dict[str, float]) -> dict:
    tp = sum(s >= threshold(t, r) and r["label"] == "scam" for s, r in scored)
    fn = sum(s < threshold(t, r) and r["label"] == "scam" for s, r in scored)
    fp = sum(s >= threshold(t, r) and r["label"] == "legit" for s, r in scored)
    tn = sum(s < threshold(t, r) and r["label"] == "legit" for s, r in scored)
    return {"n": len(scored), "recall": tp / (tp + fn) if tp + fn else float("nan"),
            "fpr": fp / (fp + tn) if fp + tn else float("nan"),
            "precision": tp / (tp + fp) if tp + fp else float("nan"), "fp": fp, "fn": fn, "auc": auc(scored)}


def auc(scored: list[tuple[float, dict]]) -> float:
    """ROC AUC: the chance a random scam scores above a random genuine message (threshold-free)."""
    scams = [s for s, r in scored if r["label"] == "scam"]
    legit = sorted(s for s, r in scored if r["label"] == "legit")
    if not scams or not legit:
        return float("nan")
    wins = sum(bisect.bisect_left(legit, s) + 0.5 * (bisect.bisect_right(legit, s) - bisect.bisect_left(legit, s)) for s in scams)
    return wins / (len(scams) * len(legit))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=0.5)
    parser.add_argument("--l2", type=float, default=1e-6)
    parser.add_argument("--max-fpr", type=float, default=0.01, help="target false-positive rate per language")
    parser.add_argument("--cv", type=int, default=5,
                        help="folds for choosing the threshold on out-of-fold scores of train + validation (0: train on train, "
                             "threshold on validation — quicker, but rests on few genuine messages)")
    parser.add_argument("--drop-cue", nargs="*", default=[], choices=sorted(CUES), help="leave out these cue features")
    parser.add_argument("--out", type=Path, default=DIST / "BASELINE.md", help="where to write the report")
    parser.add_argument("--save", type=Path, help="also write the final model (bias, thresholds, non-zero weights) as JSON")
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    ACTIVE_CUES.difference_update(args.drop_cue)
    started = time.time()

    def log(message: str) -> None:
        print(f"[{(time.time() - started) / 60:5.1f} min] {message}", flush=True)

    train_rows, val_rows, test_rows = load("train"), load("validation"), load("test")
    log(f"train {len(train_rows)}, validation {len(val_rows)}, test {len(test_rows)}")
    test_feats = featurize(test_rows)
    if args.cv:
        # Every genuine message of train and validation gets a score from a model that never saw it
        # (or its near-duplicates and variants); the threshold rests on all of them, and the final
        # model then learns from train and validation together.
        pool = train_rows + val_rows
        pool_feats = featurize(pool)
        log("features ready")
        folds = [fold_of(r, args.cv) for r in pool]
        held_out: list[tuple[float, dict]] = []
        for k in range(args.cv):
            inside = [i for i, f in enumerate(folds) if f != k]
            w, bias = train([pool[i] for i in inside], [pool_feats[i] for i in inside], args.epochs, args.lr, args.l2, args.seed)
            held_out += [(score(w, bias, pool_feats[i]), pool[i]) for i, f in enumerate(folds)
                         if f == k and pool[i]["origin"] != "augmented"]
            log(f"fold {k + 1}/{args.cv} done")
        t = pick_thresholds(held_out, args.max_fpr)
        w, bias = train(pool, pool_feats, args.epochs, args.lr, args.l2, args.seed)
        basis = f"out-of-fold scores of train + validation, {args.cv} folds"
    else:
        train_feats = featurize(train_rows)
        w, bias = train(train_rows, train_feats, args.epochs, args.lr, args.l2, args.seed)
        held_out = [(score(w, bias, f), r) for r, f in zip(val_rows, featurize(val_rows))]
        t = pick_thresholds(held_out, args.max_fpr)
        basis = "validation"
    log("final model trained")
    # A softer "be careful" level for the app, flagging up to 5% of genuine messages.
    caution = pick_thresholds(held_out, max(args.max_fpr, 0.05))
    if args.save:
        kept = {i: round(x, 6) for i, x in enumerate(w) if abs(x) >= 1e-5}
        # Messages with the scores the saved weights give them, for checking a port of the model.
        picked = sorted((r for r in test_rows if r["origin"] in OWN), key=lambda r: r["id"])
        picked = [r for r in picked if r["label"] == "scam"][:15] + [r for r in picked if r["label"] == "legit"][:15]
        golden = [{k: r[k] for k in ("lang", "source", "sender", "subject", "text")} |
                  {"score": round(sigmoid(bias + sum(kept.get(i, 0.0) * v for i, v in features(r).items())), 6)} for r in picked]
        model = {"dim": DIM, "meta_weight": META_WEIGHT, "bias": bias, "thresholds": t, "thresholds_caution": caution,
                 "golden": golden, "weights": kept}
        args.save.write_text(json.dumps(model, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        log(f"saved {len(kept)} weights to {args.save}")
    test = [(score(w, bias, f), r) for r, f in zip(test_rows, test_feats)]

    shown = ", ".join(f"{lang} {v:.3f}" for lang, v in t.items())
    legit_basis = Counter(r["lang"] for _, r in held_out if r["label"] == "legit" and r["origin"] in OWN)
    # Recall at the threshold that flags 1% of genuine *test* messages doesn't depend on the
    # threshold choice at all; with AUC it is the fairest way to compare runs.
    t_test = pick_thresholds(test, args.max_fpr)
    lines = ["# Baseline results", "",
             f"Thresholds {shown}: at most {args.max_fpr:.0%} of genuine messages flagged per language, and per channel "
             f"where it has at least {MIN_LEGIT} genuine messages, on {basis} "
             f"({legit_basis.get('pl', 0)} of our own genuine Polish messages).",
             f"\"Recall @{args.max_fpr:.0%} FPR\" instead sets the threshold on the test set itself "
             f"({', '.join(f'{k} {v:.3f}' for k, v in t_test.items())}); use it, with AUC, to compare runs.", ""]
    lines += [f"| Test subset | n | Scam recall | False-positive rate | Precision | FP | FN | AUC | Recall @{args.max_fpr:.0%} FPR |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    subsets = defaultdict(list)
    for s, r in test:
        own = r["origin"] in OWN
        subsets["all"].append((s, r))
        subsets[f"{r['lang']} all"].append((s, r))
        if own:
            subsets[f"{r['lang']} real"].append((s, r))
            subsets[f"{r['lang']} real {r['source']}"].append((s, r))
            if r["hard"]:
                subsets[f"{r['lang']} real hard"].append((s, r))
        else:
            subsets[f"{r['lang']} external"].append((s, r))
    for name in sorted(subsets, key=lambda k: (k != "all", k)):
        m = metrics(subsets[name], t)
        fixed = metrics(subsets[name], t_test)
        lines.append(f"| {name} | {m['n']} | {m['recall']:.1%} | {m['fpr']:.1%} | {m['precision']:.1%} | {m['fp']} | {m['fn']} | "
                     f"{m['auc']:.3f} | {fixed['recall']:.1%} |")

    soft = [f"{name} {metrics(subsets[name], caution)['recall']:.1%} of scams, {metrics(subsets[name], caution)['fpr']:.1%} of genuine"
            for name in ("pl real", "pl real sms", "pl real email", "pl real notification", "pl external") if subsets.get(name)]
    lines += ["", f"\"Be careful\" level (thresholds flagging up to 5% of genuine messages, saved as `thresholds_caution`): "
              + "; ".join(soft) + "."]

    if args.cv:
        # Held-out scores also cover the written messages and Ukrainian, which test (real only) can't.
        lines += ["", "## Cross-validation: held-out folds of train + validation (our own messages)", "",
                  "Every message was scored by a model that did not see it or its near-duplicates. Written messages are",
                  "cleaner than real ones, so these numbers are more optimistic than test.", "",
                  "| Subset | n | Scam recall | False-positive rate | FP | FN | AUC |", "|---|---:|---:|---:|---:|---:|---:|"]
        cv_sets = defaultdict(list)
        for s, r in held_out:
            if r["origin"] in OWN:
                cv_sets[f"{r['lang']} all"].append((s, r))
                cv_sets[f"{r['lang']} {r['origin']}"].append((s, r))
                cv_sets[f"{r['lang']} {r['source']}"].append((s, r))
                if r["hard"]:
                    cv_sets[f"{r['lang']} hard"].append((s, r))
        for name in sorted(cv_sets):
            m = metrics(cv_sets[name], t)
            lines.append(f"| {name} | {m['n']} | {m['recall']:.1%} | {m['fpr']:.1%} | {m['fp']} | {m['fn']} | {m['auc']:.3f} |")

    def mistakes(kind: str, lang: str, limit: int) -> list[str]:
        own = [(s, r) for s, r in test + held_out if r["origin"] in OWN and r["lang"] == lang]
        if kind == "fp":
            bad = sorted([(s, r) for s, r in own if r["label"] == "legit" and s >= threshold(t, r)], key=lambda x: -x[0])
        else:
            bad = sorted([(s, r) for s, r in own if r["label"] == "scam" and s < threshold(t, r)], key=lambda x: x[0])
        return [f"- {s:.2f} [{r['split']}/{r['origin']}/{r['source']}/{r['topic'] or ','.join(r['types'])}] {r['text'][:200]!r}" for s, r in bad[:limit]]

    scope = "test and held-out folds" if args.cv else "validation + test"
    names = {"pl": "Polish", "uk": "Ukrainian"}
    for lang, limit in (("pl", 60), ("uk", 20)):
        if lang in t:
            lines += ["", f"## Genuine {names[lang]} messages flagged as scams ({scope})", ""] + (mistakes("fp", lang, limit) or ["(none)"])
            lines += ["", f"## {names[lang]} scams missed ({scope})", ""] + (mistakes("fn", lang, limit) or ["(none)"])
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[:5 + len(subsets) + 2]))
    log("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
