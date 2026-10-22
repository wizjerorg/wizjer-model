# Data card — Wizjer scam messages

A dataset of scam and genuine short messages — SMS, app notifications and e-mails, mainly in
Polish, with English — for training the on-device scam detector in the Wizjer app. It combines
real messages from public warnings and genuine notices, messages written for the project,
build-time variants and optional third-party corpora.

## Layout

```
real/<lang>/<source>/<label>/<category>.jsonl      real messages, each with its public source
examples/<lang>/<source>/<label>/<category>.jsonl  messages written for the project
pools/lookalikes.json                              real look-alike domains per brand (CERT Polska)
drafts/                                            work in progress, not used by the build
```

| Origin | What it is | Used for |
|--------|------------|----------|
| `real` | Messages people actually received, quoted or shown in public warnings and genuine notices published by their senders. | train, validation and **all of test** |
| `written` | Messages written for this project in the style of documented campaigns, plus genuine-looking counterparts. Fills gaps the real data can't (rare scam types, hard negatives). | train and validation only |
| `augmented` | Variants of training messages made at build time (`--augment`). | train only |
| `external:<name>` | Third-party corpora, downloaded on demand: English SMS and e-mail datasets, and genuine everyday Polish and Ukrainian writing (Tatoeba, the National Corpus of Polish, Polish Wikipedia talk pages). | all splits |

| Path part  | Values | Meaning |
|------------|--------|---------|
| `lang`     | `pl`, `uk`, `en` | Language of the message text (brand names and links may be in other languages). |
| `source`   | `sms`, `notification`, `email` | How the message reaches the phone. `notification` covers chat and marketplace apps (WhatsApp, Messenger, Telegram, Viber, OLX, Vinted, Booking…). |
| `label`    | `scam`, `legit` | Whether the message is an attempt to defraud the reader. |
| `category` | scam type (for `scam`) or topic (for `legit`) | File name, e.g. `parcel_fee.jsonl` or `bank_codes.jsonl`. |

Each line is one JSON object. Fields implied by the path are **not** repeated in the file;
`scripts/build.py` adds them.

| Field      | Required | Description |
|------------|----------|-------------|
| `text`     | always   | The message body exactly as the recipient would see it (SMS text, notification text, e-mail body). |
| `sender`   | `email`, `notification`; optional for `sms` | SMS: sender ID or number (`InPost`, `+48 512 304 991`). Notification: chat or contact name as shown. E-mail: `Name <address>`. |
| `subject`  | `email` | E-mail subject. |
| `app`      | `notification` | App that showed the notification (`WhatsApp`, `Messenger`, `Telegram`, `Viber`, `OLX`, …). |
| `types`    | optional | Scam types when the message fits more than one, e.g. `["government", "parcel_fee"]`. Defaults to the file's category. Not allowed for `legit`. |
| `hard`     | optional | `true` for deliberately confusable examples: genuine messages that look alarming, or scams with no obvious red flags. Used for separate evaluation. |
| `campaign` | optional | Short id grouping variants of the same campaign so they always land in the same split. |
| `note`     | optional | Free-text note for reviewers (not used in training). |
| `script`   | optional | `"latin"` for Ukrainian typed in Latin letters (transliterated SMS such as "Vam dostupna vyplata"); otherwise Ukrainian must be mostly Cyrillic. |
| `source_url` | `real` only, required | The public page the message comes from. |
| `date`     | `real` only | Publication date of that page. |
| `edited`   | `real` only | Every change made to the original: placeholders filled in, links re-armed (`hxxp` → `http`), personal data replaced, OCR transcription. A real record without `edited` is verbatim. |

### Built record (`dist/*.jsonl`)

`build.py` emits one object per message with: `id` (stable hash), `lang`, `source`, `label`,
`types` (list, empty for legit), `topic` (legit category), `sender`, `subject`, `app`, `text`,
`hard`, `origin` (`real`, `written`, `augmented` or `external:<name>`), `source_url`, `license`,
`split`, `group` (the near-duplicate/campaign cluster; augmented variants share their source's
group, so cross-validation can keep them together).

## Labels

**`scam`** — the message tries to get money, payment-card data, login details, one-time or BLIK
codes, identity data (PESEL, ID number), control of the device (remote access, APK), or an
account (WhatsApp/Telegram linking codes) under false pretences. Illegal-casino advertising is
labelled `scam` (type `gambling`): it is unlawful in Poland, and many such sites are outright
fraud.

**`legit`** — everything else that a person really receives: bank codes and alerts, courier
notices, invoices, government notices, appointment reminders, marketing from real brands,
family and work chats. Many legit examples are intentionally scary or code-heavy (`hard: true`).

Ordinary marketing that is merely annoying is **legit**. Wizjer warns about fraud, not about spam.

## Scam types

| Type | What it covers | App type |
|------|----------------|----------|
| `parcel_fee` | Fake courier/post notices: top-up, customs fee, redelivery, wrong address (InPost, DPD, DHL, Poczta Polska, Nova Poshta). | ParcelFee |
| `bank` | Bank impersonation: suspicious login, blocked account, "new app / app expiring", data verification, fake "bank employee verification" SMS, "safe account". | BankImpersonation |
| `code_theft` | Requests for BLIK, SMS or app codes, WhatsApp/Telegram linking codes, "vote for me" account takeovers. | CodeTheft |
| `family` | "Mum/Dad, this is my new number", hijacked friend asking for money or BLIK, relative in trouble. | FamilyEmergency |
| `marketplace` | OLX, Vinted, Allegro Lokalnie, Otomoto, AUTO.RIA: "buyer has paid, collect the money", "verify your account to keep selling". | Marketplace |
| `investment` | Fake investment platforms, crypto "profits", celebrity-endorsed schemes, crypto-exchange alerts with a callback number, "recover your lost money". | Investment |
| `job` | Easy-money tasks (likes, reviews), Telegram/WhatsApp recruiters, "you passed the assessment, daily rate 200–800 zł". | JobTask |
| `utility` | Electricity, gas, water and telecom: arrears with disconnection threats, "overpayment refund", "double payment", SIM "update". | UtilityShutoff |
| `government` | Tax refunds/arrears, mObywatel, e-TOLL and road fines, ZUS, NFZ, social benefits, housing, e-Doręczenia, bailiffs, police/court/SBU threats. | Government |
| `prize` | Lotteries, surveys with rewards, gift cards, expiring loyalty points, cashback. | Prize |
| `remote_access` | "Install this app/APK", remote-desktop "help", fake security or banking app updates. | RemoteAccess |
| `phishing` | Account phishing for services: streaming, Apple/iCloud, mailbox quota, Booking, Steam, social media, payment apps. | Phishing |
| `gambling` | Illegal online casino and bookmaker promotions, "bonus 300% up to 5 000 zł", fake winnings. | *(new)* |
| `extortion` | Sextortion and blackmail ("we recorded you"), fake police/court/cyberpolice charges demanding payment. | *(new)* |
| `fake_shop` | Too-good-to-be-true shops and resale (tickets), subscription traps disguised as prizes or 1 € shipping. | *(new)* |
| `loan` | Fake loans and credit programmes with an upfront fee or bank login. | *(new)* |

## How the data was made

1. **Real messages.** Every public warning by CERT Orange Polska (2016–2026) was read, both
   the quoted text and every screenshot: message screenshots were transcribed with OCR and
   checked by hand. The same was done for CERT Polska's warnings (moje.cert.pl), Niebezpiecznik,
   Sekurak and Zaufana Trzecia Strona (2010–2026), Erste Bank's warnings and about 2 500
   security articles from Telepolis, Android.com.pl, Instalki, GSMManiak and Tabletowo; police
   and press warnings added more. Genuine messages come from the
   government's Alert RCB archive, the public SISMS feed of municipal notices, breach
   notifications companies sent to their customers, and genuine SMS that the same sources
   showed next to the fakes. Placeholders the sources used (`[LINK]`, `[24 cyfry]`, masked
   names) were filled with invented values or with real look-alike domains of the same brand,
   and every change is recorded in `edited`. See [sources.md](sources.md).
2. **Ordinary human writing.** Openly licensed Polish text is added as genuine messages when
   building with `--include-external`: everyday sentences from Tatoeba (CC BY), conversation
   transcripts and internet chat and forum posts from the National Corpus of Polish (NKJP-1M,
   CC BY), and comments from Polish Wikipedia user talk pages (CC BY-SA). This is unscripted
   human writing, so that plain conversation — "chyba jestem w tarapatach", "oddzwoń jak
   możesz", "możesz mi pomóc z tym artykułem?" — is not mistaken for a scam. Written
   family, friends, coworker and marketplace chats (with typos, slang and no diacritics) cover
   the messages people actually exchange, including the genuine versions of scam scenarios
   (a real "new number" text, a child asking for money with context, a buyer asking "is it
   still available?").
   **Ukrainian** follows the same plan: Tatoeba sentences, written genuine messages from the
   services Ukrainians use at home and in Poland (PrivatBank, monobank, Oschadbank, Nova
   Poshta, Ukrposhta, Diia, DTEK outage schedules, air-raid alerts, Helsi, ZUS, PESEL), natural
   chats (some mixing in Polish words, as Ukrainians in Poland write), and written scams in
   the style of documented Ukrainian schemes (fake aid payouts, "safe account", OLX "safe
   deal", hijacked friends asking to vote or lend). A few real Ukrainian scams come from
   screenshots in ITC.ua and Fakty articles. Ukrainian SMS are often typed in Latin letters;
   such records carry `"script": "latin"`.
3. **What was left out on purpose.** Messages whose text carries no sign of fraud were not
   labelled as scams, even when they were part of an attack: malware e-mails that read exactly
   like a real invoice or bank confirmation, or a "buyer" asking "is the bike still
   available?". Labelling them `scam` would teach the model to flag the genuine messages they
   copy. Example messages that the sources wrote themselves (illustrations, not received
   messages) went to `examples/` with a `note`, so the test split stays real.
4. **Research for written examples.** Campaigns observed in 2025–2026 were catalogued from
   public warnings (CERT Polska, CERT Orange Polska, NASK, banks, couriers, FTC). Each entry in
   [sources.md](sources.md) records the date, the channel, the sender IDs used, the wording
   style and what the scam ultimately asks for — in our own words.
5. **Writing.** Written examples follow each campaign's style with natural variation:
   different senders and numbers, with and without Polish diacritics, typos, obfuscation seen
   in the wild (look-alike letters, `0` for `O`, capital `I` for `l`, mojibake, spaced
   letters), short links, foreign numbers, and differing lengths and tones.
6. **Genuine counterparts.** For every scam theme there are genuine messages of the same kind
   (bank codes, courier notices, invoices, government notices, breach notifications, password
   resets), including warnings that contain scam vocabulary.
7. **Augmentation (training only).** `build.py --augment N` adds variants of training
   messages that change what a detector must ignore — amounts, codes, dates, names, tracking
   numbers, diacritics, spacing — in both classes, so none of these becomes a scam signal on
   its own. Scam variants also get other real look-alike domains of the same brand, spoofed
   senders and look-alike letters. Variants are made after the split, so none leaks into
   validation or test.
8. **Checks.** `scripts/build.py` validates every record, rejects exact duplicates, groups
   near-duplicates and campaigns so that variants never straddle splits, checks the language
   script (ignoring look-alike letters inside Latin words), and flags account numbers that
   happen to pass the IBAN checksum.

## Splits

Grouped by near-duplicate cluster and campaign. Groups with a real message: 40% test, 10%
validation, 50% train. Groups of written messages: 90% train, 10% validation, never test.
Written messages that are near-copies of a real test message are left out of the build.
External corpora: 80 / 10 / 10 by hash. **The test split measures real messages only** (plus
the external corpora), so its numbers say how the model does on what people actually
receive. Report false positives per language on the `legit` part of test: for a warning app,
a false alarm on a genuine bank code costs more trust than a missed scam.

## Privacy and safety

- In written examples, all people, phone numbers, account numbers, case numbers and
  addresses are invented. Polish account numbers are made to **fail** the IBAN checksum.
- In real messages, names of recipients, impersonated employees and hijacked senders were
  replaced with invented ones, and masked values were filled with invented ones. Public
  officials' roles in municipal notices are kept; signature lines with a person's name are
  removed.
- **Domains in `real/` and `pools/` are real malicious domains** reported by CERT teams (most
  are long dead). Don't visit them. Domains in written examples are invented and may exist by
  coincidence.
- Brand names (InPost, PKO BP, OLX…) appear because scammers impersonate them. Their presence
  says nothing about those companies.
- Messages reported by app users are never published here.

## Known limitations

- **Real data is still modest**: about 1 190 real Polish messages (≈930 SMS, 180 e-mails, 80
  chat/app notifications), half of them scams. Genuine Polish messages are mostly Alert RCB and
  municipal notices, plus breach notices and a few dozen genuine service messages, so the real
  test set measures false positives on official notices well but on bank, courier and personal
  messages only thinly; the external corpora and written chats stand in for personal messages. A
  private, consented test set of everyday messages is planned and will never be published.
- **Chat scams are the hardest part.** Single lines from a scam conversation ("I've paid,
  give me your e-mail", "what is your age and job?") often carry no fraud signal on their own;
  the app should judge such messages together with the conversation and the sender.
- **OCR.** Screenshot transcriptions were checked by hand, but link paths and look-alike
  letters may be inexact; such records say so in `edited`.
- **Coverage.** Polish SMS is the largest part; Polish e-mail is growing. English comes mostly
  from external corpora. Ukrainian is mostly written (about 200 genuine and 150 scam
  messages, plus Tatoeba) with only a handful of real messages, so its test numbers are
  anecdotal; the cross-validated scores in `dist/BASELINE.md` are the better guide for it.
- **Time.** Scams change quickly; real messages span 2016–2026 (`date`), written ones reflect
  2025–2026. New campaigns should be added as they appear.
- **Context.** A message alone can be ambiguous ("Mum, my battery died, pick me up at 6").
  The detector combines the model with link reputation, the sender (e.g. whether it's a saved
  contact) and rules; the model should not be used alone for high-stakes decisions.
