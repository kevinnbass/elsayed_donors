# El-Sayed donor-base analysis store

Canonical named itemized roster is the **most-recent F3 electronic filings**
for C00902668 (not `indiv26`, which still ends at Q1 2026).

| file | what |
|---|---|
| `roster_named_itemized.jsonl` | gift-level SA11AI (memo-X dropped) |
| `roster_summary.json` | $ totals by filing |
| `q1_amendment_delta.json` | FEC-2005719 vs indiv26 file 1996846 |
| `filings_2025_most_recent.json` | 2025 H1/Q3/YE e-file paths |
| `nppes_donor_matches.jsonl` | name+state donor rollup + NPPES verdict |
| `healthcare_share_nppes.json` | first-pass share (mixed homonyms in floor — superseded) |
| `healthcare_share_nppes_tight.json` | **use this** — mixed homonyms excluded from floor |
| `healthcare_share_nppes.md` | human summary |
| `indiv26_vintage.json` | bulk Last-Modified + ingest ledger |
| `analysis_index.json` | artifact index |
| `ingest_queue_receipt.json` | lake queue of donor JSONL |

Filings live at `K:/drain/political/fec_2026_refresh/20260816/filings/`.
Lake queue target `fec_c00902668_itemized_nppes_2026` is pending ingest
(ledger 2314354). Do not start a second ingest worker.
