# El-Sayed donor-base analysis store

Canonical named itemized roster is the **most-recent F3 electronic filings**
for C00902668 (not `indiv26`, which still ends at Q1 2026).

| file | what |
|---|---|
| `roster_named_itemized.jsonl` | gift-level SA11AI (memo-X dropped), Jan 1 2025 – Sep 30 2026, built by `scripts/build_roster.py` |
| `roster_summary.json` | $ totals by filing |
| `q1_amendment_delta.json` | FEC-2005719 vs indiv26 file 1996846 |
| `filings_2025_most_recent.json` | 2025 H1/Q3/YE e-file paths |
| `nppes_donor_matches.jsonl` | name+state donor rollup + NPPES verdict (gross $), from `scripts/nppes_share.py` |
| `sdn_screen.json` | OFAC SDN screen of every donor (`scripts/sdn_screen.py`) |
| `donors_net.jsonl` | one row per donor (name+suffix+ZIP), net of refunds and reattributions, with the committee-aggregate check |
| `top_donors.json` / `TOP100_and_by_sector.txt` | donors at the $7,000 maximum, random top 100, per-sector lists |
| `top20_physicians_and_systems.json` / `TOP20.txt` | NPPES physicians at the maximum, top 20 employers of health-care donors (net) |
| `healthcare_share_nppes.json` | first-pass share, July 15 data (mixed homonyms in floor — superseded) |
| `healthcare_share_nppes_tight.json` | **use this** — mixed homonyms excluded from floor (through Sep 30, 2026) |
| `healthcare_share_nppes.md` | human summary of the July 15 data (historical) |
| `indiv26_vintage.json` | bulk Last-Modified + ingest ledger |
| `analysis_index.json` | artifact index |
| `ingest_queue_receipt.json` | lake queue of donor JSONL |

Filings live in `data/filings/` (superseded amendments in `data/filings/superseded/`).
Lake queue target `fec_c00902668_itemized_nppes_2026` is pending ingest
(ledger 2314354). Do not start a second ingest worker.
