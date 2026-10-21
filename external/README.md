# External datasets

Optional English corpora that add volume, especially for e-mail. They are **downloaded on
demand** by `scripts/fetch_external.py` into `external/raw/` and converted into
`external/converted/`; neither folder is committed. Each dataset keeps its own licence and
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

By default `uci_sms`, `mendeley_smishing`, `nazario`, `nigerian_fraud` and `spamassassin` are
fetched (about 33 MB) and each is capped at 6 000 random records.

## Notes

- The label `spam` marks unwanted messages that are not necessarily fraud. Wizjer warns about
  fraud, so how `spam` is used in training (dropped, down-weighted, or treated as `legit`) is a
  training-time decision.
- These corpora are English, mostly older, and the e-mail ones contain real people's
  correspondence (Enron, SpamAssassin). Use them locally for training only; don't republish them
  as part of this project.
