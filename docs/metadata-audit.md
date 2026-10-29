# Missing metadata audit — 29 October 2026

## Scope and method

Inspected all 27 source records for absent or explicitly unknown license, size,
sample count, date, citation, and provenance fields. Eight records required a
closer review. This is a source-documentation audit; no raw dataset was downloaded,
counted, profiled, or relabeled. Other records' verification information was not
changed. A source becoming unavailable is not proof that it has no license.

| Record | Evidence reviewed | Decision / remaining uncertainty |
| --- | --- | --- |
| CIFAR-10 | [Toronto publisher page](https://cave.cs.toronto.edu/kriz/cifar.html) | Reconfirmed 60,000 images, 50,000/10,000 splits and 163 MB Python archive. Removed the unsupported non-commercial-only statement. No standard license grant established; commercial use stays unknown. |
| IMDb reviews | [Author's Stanford NLP documentation](https://nlp.stanford.edu/~amaas/data/sentiment/index.html) and indexed publisher documentation | Reconciled 25,000 training + 25,000 test + 50,000 unlabeled reviews: total 100,000. Removed inferred academic-use permission. Full-page retrieval failed; license remains unspecified and the record is provisional. |
| GLUE | [Publisher FAQ](https://gluebenchmark.com/faq/) including its indexed licensing answer | Original task licenses apply. Removed unverified examples of component licenses. The live site was JavaScript-only for the text fetcher; historical aggregate size/count were not reverified and the record is provisional. |
| MNIST | [NIST MNIST record](https://tsapps.nist.gov/BDbC/Search/Details/387); attempted original publisher page | Counts corroborated as 60,000 train and 10,000 test. Original source timed out; no license assigned from a mirror. License unknown, record provisional. |
| California Housing | [Maintainer distribution documentation](https://scikit-learn.org/stable/datasets/real_world.html#california-housing-dataset); attempted original archive | 20,640 rows and census provenance corroborated. Original archive unavailable; no license inferred from census or loader code. Prior 1.4 MB was not established as a distribution size and is now unknown. Record provisional. |
| Bangladeshi Banknote serial | [Mendeley version 1](https://data.mendeley.com/datasets/pw22dn2mmy/1) | Publisher describes 450 images, denominations, date, and CC BY 4.0. Download size could not be established; explicitly unknown. |
| Bangladeshi Currency Recognition | [Mendeley version 1](https://data.mendeley.com/datasets/3cv2sypkkh/1) | Reconfirmed publisher's 5,073 images, denomination breakdown, date and license. Download size remains unknown. |
| JaalTaka | [Mendeley version 2](https://data.mendeley.com/datasets/2m7wk5cy4c/2) | Reconfirmed 1,390 banknotes (802 genuine, 588 counterfeit), six views per note, date and license. The implied 8,340 views are explicitly arithmetic, not a file inventory. Download size remains unknown. |

## Follow-up policy

Unknown values are deliberate and supported by the review limits above. Fill them
only with publisher evidence for the specific release. For sizes, identify whether
the value describes an archive, extracted files, or a memory footprint. Recheck
licensing against the original distribution, and record the exact scope and date
of any later review. Provisional records retain source links and explain what is
unresolved; this audit does not invent a legal permission or a new verification team.

## Validation

Regenerated `frontend/public/data/catalog.json` from the source records. Schema,
URL syntax, uniqueness, and the Python/frontend suites are checked before merge.
