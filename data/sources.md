# Sources

## Real messages (`data/real/`)

Every record in `data/real/` carries the `source_url` of the page it comes from and the page's
publication `date`. Only the messages themselves are quoted, never the surrounding articles.

| Source | What we took | How |
|--------|--------------|-----|
| [CERT Orange Polska — warnings and news](https://cert.orange.pl/ostrzezenia/) | Scam SMS, chat messages and e-mails quoted in warnings, 2016–2026; a few genuine messages the team published as such (e.g. a real Profil Zaufany SMS, Orange e-invoices) | Quoted text copied; messages shown only as screenshots transcribed with OCR (Windows OCR, Polish) and checked by hand |
| [Sekurak](https://sekurak.pl/) | Scam messages quoted in articles or shown in screenshots; genuine data-breach notices; genuine mObywatel and Google SMS shown next to fakes | Quoted text copied; screenshots transcribed with OCR and checked by hand |
| [Niebezpiecznik](https://niebezpiecznik.pl/) | Scam SMS and e-mails from 2013–2026 screenshots; genuine breach notices companies sent to customers (Lidl, Morele, Netia, Totolotek, PZU…); a few genuine service messages (OLX code, Getin Bank, LUX MED) | As above |
| [CERT Polska — warnings (moje.cert.pl)](https://moje.cert.pl/komunikaty/) | Fake SMS and e-mails shown in CERT Polska's and CSIRT KNF's 2025–2026 warnings (parking fines, couriers, tax refunds, NFZ, Play, home.pl, Onet, SGB); the warnings are CC BY-SA 4.0 | Screenshots transcribed with OCR |
| [Zaufana Trzecia Strona](https://zaufanatrzeciastrona.pl/) | Scam SMS and e-mails 2012–2026, incl. password-protected malware e-mails; genuine notices (Google, Netia, Play, IKEA Family, mBank, eSky) | Quoted text copied; screenshots transcribed with OCR |
| News sites — [Instalki](https://www.instalki.pl/), [GSMManiak](https://www.gsmmaniak.pl/), [Tabletowo](https://www.tabletowo.pl/) | Scam messages quoted or shown in security news; genuine OLX and DPD security SMS | As above |
| Ukrainian news — [ITC.ua](https://itc.ua/), [Fakty](https://fakty.com.ua/) | Ukrainian scam messages shown in articles (aid payouts, Ukrposhta, tax debt) | Screenshots read by hand (no Ukrainian OCR available) |
| [Erste Bank (formerly Santander) — security warnings](https://www.erste.pl/klient-indywidualny/bankowosc-internetowa/bezpieczne-bankowanie/komunikaty) | Fake bank SMS and e-mails shown in the bank's own warnings | Screenshots transcribed with OCR |
| News sites — [Telepolis](https://www.telepolis.pl/tech/bezpieczenstwo), [Android.com.pl](https://android.com.pl/tag/oszustwo/) | Scam messages quoted in security news; genuine messages quoted as such (InPost pickup code, Biedronka, Ministry of Health) | Quoted text copied; screenshots transcribed with OCR |
| Police and press pages (policja.gov.pl units, gov.pl/web/gitd, Bankier, Android.com.pl…) | Scam SMS quoted in public warnings | Quoted text copied |
| [Government Centre for Security — RCB alerts](https://www.gov.pl/web/rcb/komunikaty) | Genuine Alert RCB messages (weather, floods, water, exercises), Polish letters removed as in the SMS | `scripts/collect_rcb.py` |
| [CERT Polska — wiedza](https://wiedza.cert.pl/) | A genuine bank code SMS used as a counter-example | Quoted text copied |
| [SISMS / BLISKO public feed](https://rejestracja.sisms.pl/wiadomosci) | Genuine notices from Polish towns and districts (water and power cuts, deadlines, events) | `scripts/collect_sisms.py` |

Links that a source masked (`[link]`, `https://…`) or that OCR could not read are filled with a
look-alike domain of the same brand from CERT Polska's list; each such record says so in `edited`.
Names of private people, codes and account numbers are replaced; made-up account numbers fail the
IBAN checksum.

Look-alike domains used by the augmentation step (`data/pools/lookalikes.json`) come from
[CERT Polska's public list of dangerous domains](https://hole.cert.pl/domains/v2/domains.txt)
via `scripts/make_pools.py`.

## Campaign catalogue

Public warnings that the written examples (`data/examples/`) are modelled on. Descriptions are
our own summaries; the written examples do not copy the source texts. Dates are the
publication dates of the warnings.

Main sources:

- **CERT Polska / NASK** — [wiedza.cert.pl](https://wiedza.cert.pl/), [Annual report 2025](https://cert.pl/posts/2026/04/raport-roczny-2025/), [NASK summary](https://www.nask.pl/aktualnosci/nie-technologia-a-emocje-raport-o-oszustwach-w-polskim-internecie)
- **CERT Orange Polska** — [warnings](https://cert.orange.pl/ostrzezenia/) (`co-` ids below link to `https://cert.orange.pl/ostrzezenia/<slug>/`)
- **Banks** — [PKO BP](https://www.pkobp.pl/klient-indywidualny/bankowosc-elektroniczna/bezpieczenstwo), [ING](https://www.ing.pl/aktualnosci/bankowosc-elektroniczna)
- **Ukraine** — Cyberpolice and NBU warnings as summarised by [Преса України](https://uapress.info/2026/10/05/novi-shemy-shahrajstva-u-2026-roczi-yak-rozpiznaty-aferystiv-i-ne-vtratyty-groshi/), [StopFraud](https://stopfraud.gov.ua/)
- **US** — [FTC: spam text messages](https://consumer.ftc.gov/articles/how-recognize-and-report-spam-text-messages)

## Overview and trends

| ID | Date | What it tells us |
|----|------|------------------|
| cert-phishing-guide | 2026 | CERT's guide: lures arrive by SMS, e-mail, ads with celebrities, group posts, hijacked friends' DMs ("vote for me"), marketplace "buyer paid", fake search ads, QR stickers on parking meters. Targets: card data under a small-fee pretext, BLIK "to receive money", SMS codes retyped "to confirm a payout", PESEL/ID photos and selfies, app installs, remote desktop, fake captcha commands. Red flags: time pressure, emotion, tiny amounts, odd channel, unexpected contact. |
| cert-report-2025 | 2026-04 | Most common 2025 campaigns: tax refunds (e-Urząd Skarbowy), InPost/Poczta Polska parcels (incl. "reply to activate the link"), e-Doręczenia letters, gov.pl "call this number" notices leading to remote access, social-benefit eligibility checks asking for PESEL, e-TOLL, statistics office malware, Baltic Pipe/Orlen investments, NFZ medicine refunds, electricity overpayment refunds. SMS trend: fewer links, more "bait to make contact" (child's new number, profits on your investment account, crypto login alerts with a phone number). |
| nask-report-2025 | 2026-04 | 97% of 2025 incidents were fraud; ~250k malicious domains; most impersonated: OLX, Allegro, banks, couriers, Poczta Polska, Profil Zaufany, gov.pl. Investment scams the fastest-growing; electricity cut-off threats over 90 gr. |
| co-sms-stats | 2026-07-22 | Most SMS blocked by Orange are illegal-casino ads; "Mum/Dad" messages are 5–12% weekly; parcel, Netflix, tax lures each <1%. "Mum" messages carry `wa.me/<number>` links. ([nielegalne-kasyna-i-nie-tylko-jak-rozpoznac-sms-y-od-oszustow](https://cert.orange.pl/ostrzezenia/nielegalne-kasyna-i-nie-tylko-jak-rozpoznac-sms-y-od-oszustow/)) |
| co-smishing-guide | 2026-06-11 | Typical smishing scenarios: parcel top-up, bank login alert, BLIK for a "child", energy invoice with disconnection, ZUS arrears with bailiff threat, Netflix suspension. ([falszywy-sms-zobacz-jak-rozpoznac-smishing](https://cert.orange.pl/ostrzezenia/falszywy-sms-zobacz-jak-rozpoznac-smishing/)) |

## Parcels and couriers (`parcel_fee`)

| ID | Date | Channel | Pattern |
|----|------|---------|---------|
| co-inpost-customs | 2026-10-20 | SMS | Parcel "subject to customs fee 5,00 zł", fresh domain, then address and full card data. |
| co-inpost-whatsapp | 2026-06-17 | SMS (sender "Inpost", lands in the real thread) | "Parcel sent to your phone number" → pick a parcel locker → "verify via WhatsApp" linking code → account hijack. |
| co-poczta-customs-mail | 2026-06-03 | e-mail | "Parcel held for customs inspection", 16,40 zł duty, sender on a hijacked foreign domain. |
| co-dpd-sms | 2026-06-29 | SMS (verify-DPD, verify-sms, +212 numbers) | "Address verification failed", redelivery fee in EUR. |
| co-dpd-mail | 2026-04-21 | e-mail | Undelivered parcel, fee of 1–2 zł, address then card. |
| co-dhl-outage | 2025-07-08 | SMS (sender "DHL") | After a real DHL outage; domains mimic InPost/Poczta, 1,08 zł. |
| co-poczta-bitly | 2025-01-29 | SMS (+48) | "Your parcel is waiting for delivery, confirm the 7,99 zł charge" via bit.ly. |
| co-poczta-held | 2025-01-13 | SMS (sender "Poczta", +48) | "Your parcel was stopped, settle the costs", "wrong address, confirm within 12 hours" via is.gd. |
| cert-reply-to-activate | 2025 | SMS | Asks the recipient to reply so the phone makes the link clickable. |

## Banks and payments (`bank`, `code_theft`)

| ID | Date | Channel | Pattern |
|----|------|---------|---------|
| pko-new-app | 2026-09-17 | SMS, e-mail | "Your mobile app will expire, install the new version"; "we changed the login page, confirm your details". |
| co-bank-verification-sms | 2026-09-15 | SMS (alior24, ing24, ipko24, iko24, PEKA024, NBP…) | No link: "bank employee verification code, ask the adviser you are talking to for it, case handled by <name>" — sent during a scam call. |
| co-erste-rebrand | 2026-05-13 | ad, SMS (+48) | After Santander→Erste rebrand: 1200 zł bonus for "activating" the app; "suspicious login, secure your account" via e.vg. |
| co-alior-mail | 2026-10-14 | e-mail | Urgent data confirmation, threat of block; look-alike login domain; collects ID data. |
| co-bank-app-sms | 2025-03-04 | SMS (+48) | App problems, expiring registration, new improved app, final verification deadline. |
| co-bnp-croatia | 2025-04-14 | SMS (+385) | Verify account or it will be blocked; asks PESEL and mother's maiden name. |
| co-blik-update | 2025-04-28, 2025-11-21 | SMS (sender "BLIK", +45 number) | "Mandatory security update of your BLIK account" citing a nameless law; blik-pl look-alike; bank picker. |
| co-blik-scenarios | 2026-07-09 | SMS, WhatsApp, Messenger | Child asks BLIK for 500 zł; friend's hijacked account asks BLIK for 300 zł; "bank" asks for BLIK to "verify identity" (ATM cash-out). |
| co-mastercard-points | 2025-11-26 | SMS (Mastercard) | Loyalty points expire in 24 h, >1000 zł cashback for credit cards, 1 zł "security" charge. |
| co-santander-points | 2026-01-08 | SMS (Santander) | Non-existent "Santander points" expiring. |
| ing-warnings | 2026 | various | Fake bank staff with ID scans, "secure your money", courier collects card/phone, "loan taken in your name", telecom/energy arrears SMS. |

## Family and friends (`family`)

| ID | Date | Channel | Pattern |
|----|------|---------|---------|
| co-new-number | 2026-10-21 | SMS (ordinary numbers) | "Mum/Dad, I lost my phone / it broke, this is my new number, write to me on WhatsApp". Deliberate typos and mojibake to evade filters. Later: urgent bill or new phone, promise to pay back. |
| cert-child-contact | 2026-04 | SMS | Child's phone or SIM damaged, contact via another messenger. |
| ua-deepfake-relative | 2026 | voice, messengers | AI-cloned voice of a relative asking for urgent money, "don't call anyone". |

## Marketplaces (`marketplace`)

| ID | Date | Channel | Pattern |
|----|------|---------|---------|
| co-olx-verify | 2026-09-09, 2026-10-01 | SMS (Verify, Alert, Autoryzacja, Weryfikator…) | "Problem with publication / verify your account", link to a clone of your listing, then bank login. |
| co-olx-whatsapp | 2026-05-11 | WhatsApp, e-mail | Buyer with a family photo, "courier will pack it", then e-mail "OLX wysyłka" from a foreign domain → fake bank. |
| co-olx-email-ask | 2025-09-19 | OLX chat, e-mail | Buyer asks for your e-mail inside OLX, then a fake InPost payout e-mail. |
| co-otomoto-qr | 2026-03-20 | Otomoto message | "Security team" message with QR code, 3,95 zł "identity confirmation", phone call. |

## Investments, crypto, gambling (`investment`, `gambling`)

| ID | Date | Channel | Pattern |
|----|------|---------|---------|
| co-investment-x | 2026-09-24 | ads | Celebrity "interview" on a fake news site, chatbot collects contacts, 1100 zł deposit. |
| co-binance | 2025-10-07 | SMS (Binance, Binance-PL, Route) | Withdrawal verification codes or "login from <country>" plus a number to call; seed phrase sent by SMS. |
| co-casino-sms | 2026-07-22, 2026-10-07, 2026-01-29 | SMS (casino names, women's first names) | Bonus ladders, free spins, "we sent 7000 zł to your number", "you're a champion", Telegram channels, deposits via BLIK. |
| co-worldcup-betting | 2026-06-11 | ads | Deepfake sportswomen promoting a fake bookmaker for the 2026 World Cup. |
| cert-investment-sms | 2026-04 | SMS | "Profits on your currency/investment account", call or reply. |
| ua-recovery | 2026-08 | calls | "We'll recover your lost investment" → remote access → loans. |

## Jobs (`job`)

| ID | Date | Channel | Pattern |
|----|------|---------|---------|
| co-job-telegram-2026 | 2026-09-24 | SMS (Adecco, Indeed, Randstad, TikTok, Telegram…) | "Jason" offers paid tasks liking TikTok videos on Telegram; growing transfers, then theft. |
| secawa-35eur | 2026-09-22 | SMS | Remote work 35 €/h, 10 € bonus for replying, 30 vacancies, Telegram recruiter. |
| co-job-assessment | 2025-08-27 | SMS (women's first names) | "You passed the assessment, daily rate 200–800 zł, contact us on Telegram". |
| ing-likes-job | 2026 | ads, SMS | "Earn online watching videos and liking posts". |
| co-orange-recruiter | 2026-01-15 | Messenger | Fake recruiter pays 100 zł for logging into a "Mój Orange" clone. |

## Bills and telecoms (`utility`)

| ID | Date | Channel | Pattern |
|----|------|---------|---------|
| co-pge-freeze | 2026-02-25 | e-mail | Two e-mails about the energy price-freeze settlement and a wrongly charged fee; "verify your data" for a refund. |
| co-pge-refund | 2025-11-04, 2026-01-08 | e-mail, SMS (+48) | Refund after a "state decree" on energy prices; odd amounts. |
| co-play-double | 2026-07-07 | SMS (Play24) | "Double payment for invoice, check". |
| co-orange-sim | 2026-04-07 | SMS | "Verify your number to avoid card block", "your SIM needs an update", t.co links. |
| co-orange-8zl | 2025-07-24 | SMS (Wsparcie) | Services suspended unless you pay 8 zł. |
| co-orange-flex | 2025-05-06 | SMS (+33, +49, ORNGE, ORFLEX) | Contract ending, card deactivation. |
| ing-telecom-arrears | 2026 | SMS, e-mail | Telecom invoice arrears, gas or electricity debt. |

## Government and public services (`government`)

| ID | Date | Channel | Pattern |
|----|------|---------|---------|
| co-tax-arrears | 2026-10-14 | SMS (Urzad.pl, e-Urzad, MyGOV, TKINFO) | Vague tax consequences; fake e-Urząd Skarbowy, then bank picker. |
| co-tax-refund-mail | 2026-05-28, 2026-08-20 | e-mail (spoofed @podatki.gov.pl), SMS | "URGENT: approve your tax refund in PUESC", legal citation; SMS "tax refund available, confirm your data". |
| co-epit | 2026-02-11 | SMS (GOV, MOF) | "The government owes you money"; bank picker. |
| co-pit-season | 2026-04-29 | SMS | Underpayment threats or overpayment refunds during the PIT season. |
| co-bailiff | 2025-03-26 | SMS (WINDK_GOVPL) | Unpaid income tax, bailiff enforcement, reference number; BLIK or card only. |
| co-mobywatel-fine | 2026-05-29 | SMS | "[mObywatel] Case no… speeding… 50% discount for 24 h… vehicle will fail inspection"; .cc domain; broken Polish. |
| co-traffic-fine | 2026-05-08, 2026-09-08 | SMS, iMessage (mObywatel, mDowod, GITD-like) | Invented authorities, "reply to this message", fake CEPiK, plate number then card. |
| co-etoll | 2026-02-25 | SMS (e-T0LL) | Unpaid toll, plate number, short links. |
| co-parking | 2026-07-02 | SMS (+212) | Unpaid parking 8 zł, .ink domain. |
| co-mobywatel-cert | 2026-07-30, 2026-09-03 | SMS | Certificate renewal deadline; "your data loses validity"; only "log in with your bank". |
| co-mops-housing | 2026-07-31 | SMS (MOPS) | "Your housing application needs completing", short link; PESEL, ID number, card. |
| co-nfz | 2025-07-16, 2026-05-15 | SMS, e-mail | NFZ refund after "billing error"; "your health insurance payment failed, update within 24 h". |
| co-zero-procent | 2025-11-06 | SMS (Kredyt) | "Application approved, finish the process" for a fake state credit programme. |
| cert-edoreczenia | 2025 | e-mail | Unclaimed official letter will be deleted; mailbox credentials. |
| cert-social-benefits | 2025 | ads | "Check your eligibility for extra benefits" with only a PESEL. |
| co-doctors | 2025-04-10, 2025-09-04, 2026-06-02 | SMS (P-1 ZDROWIE, Gabinet, MD-FILE) | Account suspended / enable 2FA in 24 h / GDPR breach fine — credential theft for doctors' systems. |
| mydr-leak | 2026-08/09 | SMS, calls | After the MyDr breach: genuine notices to patients (legit) and scams: "your data is on the darknet, click to see", fake leak checker, "compensation" help. |
| migrants-pl | 2026 | calls, SMS | Fake voivodeship office or lawyer: "your residence decision is ready, pay the fee"; ZUS/800+ payout lures. |

## Subscriptions and online services (`phishing`)

| ID | Date | Channel | Pattern |
|----|------|---------|---------|
| co-netflix | 2026-07-01, 2025-03-03, 2025-04-14 | SMS (Wsparcie, Obsługa, +33, +49) | Account blocked / payment declined; look-alike domains (letters swapped). |
| co-apple-pay | 2026-06-24 | SMS (Apple Pay) | English: "your wallet is no longer verified / inactive, reactivate". |
| co-icloud | 2026-01-14 | e-mail (spoofed senders) | Storage full, photos will be deleted, "upgrade now for 7 zł". |
| co-booking | 2026-09-04, 2026-07-09, 2025-08-04 | SMS, WhatsApp, Booking chat | Real reservation details from hacked hotel accounts, "confirm your card". |
| co-skrill | 2026-06-30 | SMS (SKRL) | Account will be permanently limited unless you confirm data. |
| co-steam | 2026-09-14 | TikTok, web | Skin giveaway → fake trade offer → typosquatted login. |
| co-telegram-verify | 2026-03-09 | SMS (Telegram) | "Your account needs additional verification" → fake web login; fake WhatsApp update APK ads. |
| co-chatgpt | 2026-03-13 | e-mail | Update payment method to keep Plus. |
| co-spotify | 2025-05-15 | e-mail | Account suspended; Shopify link resembling Spotify. |
| co-disney | 2025-06-26 | e-mail | Subscription suspended after a promo. |
| co-homepl | 2026-05-12 | e-mail | Pay for the domain or lose it. |
| co-fakturownia | 2026-09-29 | e-mail | After an invoicing-service breach: "unblock account", "regenerate API token". |
| co-invoice-malware | 2025-03-17, 2025-03-19, 2026-04-08 | e-mail | Fake invoice or transfer confirmation with ZIP/ISO attachment (malware). |

## Prizes, shops, loans (`prize`, `fake_shop`, `loan`)

| ID | Date | Channel | Pattern |
|----|------|---------|---------|
| co-allegro-prize | 2025-02-03 | SMS (NOTICE) | 2750 zł gift card for an Allegro survey. |
| co-iphone-survey | 2025-10-10 | e-mail | Survey prize iPhone, pay 1 € shipping → subscription. |
| co-castorama | 2025-11-14 | e-mail | Drill for 8,80 zł after a survey → subscription. |
| co-tickets | 2025-06-12 | social posts | Sold-out concert tickets via a ticketing look-alike. |
| co-fake-shops | 2025-12-12, 2026-03-12 | ads | Pharmacy and fashion brand clones with absurd discounts. |
| co-lokata | 2025-12-03 | ads, WhatsApp | Fake bank deposit with PESEL and bank login. |

## Ukrainian (`uk`)

| ID | Date | Pattern |
|----|------|---------|
| ua-bank-call | 2026 | "Bank security": suspicious payment, asks for CVV, PIN, SMS code, or transfer to a "safe / reserve / technical account". |
| ua-payouts | 2026-08 | Fake state aid, pension top-ups (3 200–5 300 UAH), compensation — "enter card details to receive". |
| ua-state-threats | 2026 | Letters from "court", "MVS", "SBU", even "Cyberpolice" with invented charges, payment in crypto; fake traffic fines. |
| ua-delivery | 2026 | Delivery problem, small top-up via link. |
| ua-diia-apk | 2026 | Fake Diia app sent as a file in Telegram/Viber. |
| ua-utility | 2026-09 | Fake electricity bills. |
| ua-autoria | 2026 | AUTO.RIA marketplace scams. |

## English (`en`)

| ID | Date | Pattern |
|----|------|---------|
| ftc-texts | 2022 (still current) | Prizes and gift cards, low-interest cards, student-loan help, "suspicious activity", "problem with your payment information", fake invoices asking you to call if you didn't authorise them, fake delivery notices. |
| co-booking-en | 2026-09-04 | Booking.com messages in English with real reservation details. |
| co-apple-pay-en | 2026-06-24 | Apple Pay wallet "no longer verified". |

## Open datasets (optional, fetched by `scripts/fetch_external.py`)

| Dataset | Licence | Use |
|---------|---------|-----|
| [SMS Spam Collection](https://doi.org/10.24432/C5CC84) — Almeida & Hidalgo, UCI | CC BY 4.0 | English SMS ham/spam (spam is mostly older UK premium-rate scams). |
| [SMS Phishing Dataset](https://doi.org/10.17632/f45bkkt8pr.1) — Mishra & Soni, Mendeley | CC BY 4.0 | English ham / spam / smishing. |
| [Phishing Email Curated Datasets](https://doi.org/10.5281/zenodo.8339691) — Champa, Rabbi & Zibran | CC BY 4.0 | English e-mails: Nazario phishing, Nigerian fraud, SpamAssassin, CEAS-08, Enron. |
| [Tatoeba](https://tatoeba.org/) — Polish and Ukrainian sentences | CC BY 2.0 FR | Everyday sentences as genuine chat/SMS text (6000 per language sampled; each keeps its tatoeba.org link). Teaches the model what ordinary human writing looks like, so plain conversation is not flagged. |
| [NKJP-1M](https://clip.ipipan.waw.pl/NationalCorpusOfPolish) — National Corpus of Polish, manually annotated subcorpus v1.2 | CC BY | Conversation transcripts, internet chat and forum posts and letters as genuine Polish messages (about 5 900 utterances and posts). |
| [Polish Wikipedia](https://pl.wikipedia.org/) user talk pages (random sample, MediaWiki API) | CC BY-SA 4.0 | Signed comments between editors, with signatures and markup removed, as genuine Polish messages (about 4 900). Each keeps its page link. |
