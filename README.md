# Wizjer model

Open data and code for the on-device scam detector in the [Wizjer](https://wizjer.org) app,
which warns people in Poland about scam SMS messages, notifications and e-mails.

The model runs **entirely on the phone**: messages are analysed locally and never sent
anywhere. This repository holds everything needed to rebuild it — the training data, the
scripts that check and package it, and (soon) the training and export code.

> **Status:** dataset v0.1. Training, distillation and LiteRT export come next.

## What's inside

```
data/
├── README.md        Data card: schema, labels, scam types, methodology, privacy, limits
├── sources.md       Where every real message comes from, and the campaigns behind the written ones
├── real/            Real messages from public warnings and genuine notices, each with its source
├── examples/        Messages written for the project (scam campaigns and genuine counterparts)
│   └── <lang>/<source>/<label>/<category>.jsonl
└── pools/           Real look-alike domains per brand (CERT Polska), used for augmentation
external/            Optional third-party datasets (downloaded locally, never committed)
scripts/
├── build.py            Validate, de-duplicate and split → dist/
├── augment.py          Training-only variants (used by build.py --augment)
├── fetch_external.py   Download and convert the third-party datasets
├── train_baseline.py   A small reference classifier and its error report → dist/BASELINE.md
├── make_pools.py       Refresh the look-alike domains
├── collect_rcb.py      Genuine Alert RCB messages from gov.pl
└── collect_sisms.py    Genuine municipal notices from the public SISMS feed
```

- **Languages:** Polish (`pl`), Ukrainian (`uk`), English (`en`)
- **Channels:** `sms`, `notification` (WhatsApp, Messenger, Telegram, marketplace apps…), `email`
- **Labels:** `scam` or `legit`, plus one or more scam types (parcel fee, bank, BLIK code theft,
  "new number" family scam, marketplace, investment, job, bills, government, prize, remote
  access, phishing, gambling, extortion, fake shop, loan)

Real messages come from public warnings (CERT Orange Polska, Niebezpiecznik, Sekurak, banks,
police, security news) and from genuine senders (Alert RCB, municipal notices, breach
notifications companies sent to customers); each one links to its source. Written messages
fill the gaps: rarer campaigns, everyday conversations, and genuine messages that *look* like
scams — bank codes, courier notices, breach notices, bank warnings — so the model learns not to
raise false alarms. See [data/sources.md](data/sources.md) and the
[data card](data/README.md).

## Build the dataset

Python 3.10+ with only the standard library:

```bash
python scripts/build.py
```

This checks every record, removes duplicates, keeps near-identical variants of a message in the
same split, and writes `dist/train.jsonl`, `dist/validation.jsonl`, `dist/test.jsonl` and
`dist/STATS.md`.

To add the optional third-party corpora (English SMS spam/smishing and phishing e-mails, CC BY
4.0; everyday Polish and Ukrainian writing from Tatoeba, the National Corpus of Polish and
Polish Wikipedia talk pages, CC BY / CC BY-SA) and training-only variants of each message:

```bash
python scripts/fetch_external.py
python scripts/build.py --include-external --augment 4
```

The test split contains real messages only; see [data/README.md](data/README.md) for how the
real data was gathered.

## Baseline

`scripts/train_baseline.py` trains a small logistic-regression classifier (character and word
n-grams plus a few message features: links, brand/link mismatch, an e-mail sender whose
address doesn't match the brand it names, look-alike letters, and Polish and Ukrainian cues such
as urgency, payment, code requests, attachments and "call our security department") on `dist/`.
The decision thresholds, per language and per channel
where there are enough genuine messages, flag at most 1% of genuine messages, measured with
grouped cross-validation over train and validation so that they rest on every genuine message
rather than the few in validation; the final model then trains on both. It
writes `dist/BASELINE.md`: test results per language and channel (with AUC and recall at 1%
false positives, the figures to compare runs by), and the genuine messages it flags and scams it
misses — the list to work from when adding data. A run takes about half an hour on a laptop;
`--cv 0` is a quicker single model with the threshold set on validation.

```bash
python scripts/train_baseline.py
```

To use the model in the app, save it and pack it into one 2 MB file (16-bit weights, the
thresholds, softer "be careful" thresholds that flag up to 5% of genuine messages, and test
messages with their scores for checking a port of the feature code):

```bash
python scripts/train_baseline.py --save dist/model.json
python scripts/export_model.py dist/model.json dist/wizjer-baseline.bin
```

Other tools: `scripts/make_pools.py` refreshes the look-alike domains from CERT Polska's public
list; `scripts/collect_rcb.py` and `scripts/collect_sisms.py --hours 24` collect genuine
government and municipal messages.

## Privacy

- No private person's messages are in `data/`. Real messages were already public (warnings,
  official notices); names of recipients and impersonated people, codes and account numbers in
  them were replaced. Everything in written examples is invented; account numbers
  deliberately fail the checksum.
- **Domains in `data/real/` and `data/pools/` are real malicious domains** from public
  warnings and CERT Polska's list. Do not visit them.
- Messages that users of the app report are **never** added to this public dataset.
- Third-party corpora are downloaded on demand and keep their own licences; they are not
  redistributed here.

## Contributing

New campaigns appear every week. A message quoted in a public warning goes to the matching
`data/real/...` file with its `source_url`, `date` and an `edited` note for anything you
changed; a message you write yourself goes to `data/examples/...`. Add the campaign to
[data/sources.md](data/sources.md) if it's new, and run `python scripts/build.py` — it will
tell you about anything wrong. Don't add messages that contain someone's personal data.

## License

[MIT](LICENSE). Third-party datasets fetched by `scripts/fetch_external.py` are licensed by
their authors (see [external/README.md](external/README.md)).
