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
├── sources.md       Real campaigns the examples are modelled on (dated, with links)
└── examples/        The dataset, one JSONL file per language / channel / label / category
    └── <lang>/<source>/<label>/<category>.jsonl
external/            Optional third-party datasets (downloaded locally, never committed)
scripts/
├── build.py         Validate, de-duplicate and split → dist/
└── fetch_external.py  Download and convert the third-party datasets
```

- **Languages:** Polish (`pl`), Ukrainian (`uk`), English (`en`)
- **Channels:** `sms`, `notification` (WhatsApp, Messenger, Telegram, marketplace apps…), `email`
- **Labels:** `scam` or `legit`, plus one or more scam types (parcel fee, bank, BLIK code theft,
  "new number" family scam, marketplace, investment, job, bills, government, prize, remote
  access, phishing, gambling, extortion, fake shop, loan)

Every example was written for this project, modelled on publicly documented campaigns
(CERT Polska, CERT Orange Polska, banks, Ukrainian Cyberpolice and others — see
[data/sources.md](data/sources.md)). Genuine messages that *look* like scams — real bank codes,
courier notices, data-breach notices, bank warnings — are included on purpose, so the model
learns not to raise false alarms.

## Build the dataset

Python 3.10+ with only the standard library:

```bash
python scripts/build.py
```

This checks every record, removes duplicates, keeps near-identical variants of a message in the
same split, and writes `dist/train.jsonl`, `dist/validation.jsonl`, `dist/test.jsonl` and
`dist/STATS.md`.

To add the optional English corpora (SMS spam/smishing and phishing e-mails, all CC BY 4.0)
and training-only variants of each message:

```bash
python scripts/fetch_external.py
python scripts/build.py --include-external --augment 4
```

Other tools: `scripts/make_pools.py` refreshes the look-alike domains from CERT Polska's public
list, and `scripts/collect_sisms.py --hours 24` collects genuine municipal notices. The test
split contains real messages only; see [data/README.md](data/README.md) for how the real data
was gathered.

## Privacy

- No real people's messages are in `data/`. Names, phone numbers, account numbers and
  addresses in the examples are invented; account numbers deliberately fail the checksum.
- Malicious-looking domains in the examples are invented too, apart from patterns described
  in the cited public warnings. Do not visit them.
- Messages that users of the app report are **never** added to this public dataset.
- Third-party corpora are downloaded on demand and keep their own licences; they are not
  redistributed here.

## Contributing

New campaigns appear every week. To add examples, put them in the matching
`data/examples/...` file (one JSON object per line), add the campaign to
[data/sources.md](data/sources.md) if it's new, and run `python scripts/build.py` — it will
tell you about anything wrong. Please write examples in your own words; don't paste messages
that contain someone's personal data.

## License

[MIT](LICENSE). Third-party datasets fetched by `scripts/fetch_external.py` are licensed by
their authors (see [external/README.md](external/README.md)).
