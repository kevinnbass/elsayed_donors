# El-Sayed cycle named-itemized physician share (NPPES-tight)

**Use `healthcare_share_nppes_tight.json` as the numbers.** The first-pass
`healthcare_share_nppes.json` counted mixed-name NPPES hits in the floor;
that is superseded.

## Roster (most-recent F3 e-files, memo-X dropped)

Named itemized: **$10,265,431.61** / 31,180 gifts. Gap vs Form 3 line 11a(i): **$0.00**.
Unitemized (still unnamed): **$4,142,626.45**.

Q1 amendment `FEC-2005719` vs `indiv26` file `1996846`: **+$7,868.83** (5 gifts).

## NPPES last+first+state (entity_type=1, taxonomy 207/208)

Floor rule: unique NPI is 207/208, **or** every same-name+state NPI is 207/208.
Mixed homonyms are **not** in the floor.

| Cut | $ | % of $10.26M named |
|---|---:|---:|
| NPPES-confirmed physician **floor** | **2,061,368.42** | **20.08** |
| of which FEC also said physician | 1,606,401.19 | 15.65 |
| of which FEC silent (consultant / retired / specialist title) | 454,967.23 | 4.43 |
| Mixed homonym (excluded from floor) | 209,024.38 | 2.04 |
| FEC "PHYSICIAN" but unique NPPES is not 207/208 (dropped) | 146,398.00 | 1.43 |
| FEC physician, no NPPES hit | 509,230.05 | 4.96 |
| **Upper bound** (floor + unmatched + mixed + leftover) | **2,780,347.85** | **27.08** |

Last+first+state is identity inference. Unique matches can still be the wrong
person (e.g. a MI dentist sharing a name with an ophthalmologist NPI).

## indiv26

Bulk `Last-Modified` still `Sun, 16 Aug 2026 15:50:15 GMT` (same 2,098,465,857
bytes). No newer file to wait for today. Canonical store is the e-files under
`K:/drain/political/fec_2026_refresh/20260816/filings/` plus this directory.
Queued `fec_individual_contributions_2026` ledger 2314349 is still pending;
no second ingest worker started.
