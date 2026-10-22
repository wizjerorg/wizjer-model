# External datasets

Optional corpora that add volume: English SMS and e-mail, and everyday Polish sentences. They
are **downloaded on demand** by `scripts/fetch_external.py` into `external/raw/` and converted
into `external/converted/`; neither folder is committed. Each dataset keeps its own licence and
must be cited if you use it.

| Name | Dataset | Licence | Size | Mapping |
|------|---------|---------|------|---------|
| `uci_sms` | Almeida & Hidalgo, *SMS Spam Collection*, UCI ML Repository, [doi:10.24432/C5CC84](https://doi.org/10.24432/C5CC84) | CC BY 4.0 | 0.2 MB, 5 574 SMS | ham → `legit`, spam → `spam` |
| `mendeley_smishing` | Mishra & Soni, *SMS Phishing Dataset for Machine Learning and Pattern Recognition*, Mendeley Data, [doi:10.17632/f45bkkt8pr.1](https://doi.org/10.17632/f45bkkt8pr.1) | CC BY 4.0 | 0.2 MB, 5 971 SMS | ham → `legit`, smishing → `scam`, spam → `spam` |
| `nazario` | Champa, Rabbi & Zibran, *Phishing Email Curated Datasets*, Zenodo, [doi:10.5281/zenodo.8339691](https://doi.org/10.5281/zenodo.8339691) — Nazario phishing corpus | CC BY 4.0 | 7.8 MB | phishing → `scam`, rest → `legit` |
| `nigerian_fraud` | same collection — advance-fee fraud | CC BY 4.0 | 9.2 MB | fraud → `scam`, rest → `legit` |
| `spamassassin` | same collection — SpamAssassin public corpus | CC BY 4.0 | 14.9 MB | spam → `spam`, ham → `legit` |
| `ceas08` | same collection — CEAS 2008 | CC BY 4.0 | 67.9 MB | spam → `spam`, ham → `legit` |
| `enron` | same collection — Enron | CC BY 4.0 | 44.8 MB | spam → `spam`, ham → `legit` |
| `tatoeba_pl`, `tatoeba_uk` | [Tatoeba](https://tatoeba.org/) Polish and Ukrainian sentences (per-language exports) | CC BY 2.0 FR | 1.7 MB / 2.5 MB | all → `legit` (as `sms` or `notification`, topic `conversation`); each record keeps its `tatoeba.org/sentences/show/<id>` link for attribution |
| `nkjp1m` | [National Corpus of Polish](https://nkjp.pl/), 1-million-word manually annotated subcorpus v1.2 (Przepiórkowski et al.) — conversation transcripts, internet forum and chat texts, letters | CC BY | 39 MB | all → `legit` (conversation → `sms` or `notification`; internet texts → `notification`, or `email` when long); topic `conversation` |
| `wiki_pl_talk` | Polish Wikipedia user talk pages, random sample via the MediaWiki API; one record per signed comment, signatures, templates and markup removed, bot and template messages dropped | CC BY-SA 4.0 | ~3 000 pages | all → `legit` (`notification`, or `email` when long); topic `conversation`; each record keeps its page link |

All datasets are fetched by default (about 200 MB) and each is capped at 6 000 random records
(`--max-per-source`).

## Notes

- The label `spam` marks unwanted messages that are not necessarily fraud. Wizjer warns about
  fraud, so how `spam` is used in training (dropped, down-weighted, or treated as `legit`) is a
  training-time decision.
- The English corpora are mostly older, and the e-mail ones contain real people's
  correspondence (Enron, SpamAssassin). Use them locally for training only; don't republish them
  as part of this project.
- Tatoeba sentences are single sentences, many translated from English, so they are ordinary
  human Polish rather than real SMS. They teach the model what normal writing looks like; the
  decision threshold is still chosen on the project's own genuine messages.
- NKJP conversations are transcribed speech and its internet texts are forum and chat posts
  from the 2000s; Wikipedia talk comments are discussions between editors. None of them is a
  real SMS, but together they give the model thousands of natural, unscripted Polish messages
  with typos, slang, questions and requests, so that ordinary talk is not read as fraud.
- Wikipedia talk comments are signed by their authors: the converter drops signatures, but
  usernames may still appear in the text. Like the other corpora, use them locally for
  training and don't republish the converted files.
