# Dollar reconciliation — Abdul El-Sayed / ABDUL FOR U.S. SENATE (C00902668)

Coverage window for published totals: **2025-01-01 through 2026-07-15** (OpenFEC candidate `S6MI00418` + committee `C00902668`, last report PRE-PRIMARY).

All figures USD. Arithmetic identities are shown, not waved.

## A. FEC-published Form 3 totals (OpenFEC, live 2026-08-16)

| line | amount |
|---|---:|
| receipts | 14,514,335.93 |
| individual_contributions | 14,408,058.06 |
| of which individual_itemized | 10,265,431.61 |
| of which individual_unitemized | 4,142,626.45 |
| other_political_committee_contributions | 71,845.23 |
| transfers_from_other_authorized_committee | 0.00 |
| candidate_contribution | 0.00 |
| offsets_to_operating_expenditures | 34,427.99 |
| other_receipts | 4.65 |
| refunded_individual_contributions | 68,392.39 |

Identity (receipts roll-forward):

```
10,265,431.61 + 4,142,626.45 + 71,845.23 + 0 + 0 + 34,427.99 + 4.65
= 14,514,335.93
```

Identity (individual):

```
10,265,431.61 + 4,142,626.45 = 14,408,058.06
```

## B. Lake `fec_itcont_2026` (pre-refresh, ingested 2026-04-08 from `errored` shard files)

| measure | value |
|---|---:|
| rows C00902668 | 8,344 |
| sum all | 3,919,770 |
| sum 15+15E non-memo (itemized individual) | 3,892,470 |
| sum 22Y (refunds stored as positive) | 16,800 |
| distinct names | 2,984 |
| name+zip keys | 3,040 |
| min/max TO_DATE(transaction_dt) | 2025-03-10 .. 2025-12-31 |

`lake.fec_individual_contributions` has **0** rows for C00902668.

Lake vs Form 3 itemized:

```
10,265,431.61 − 3,892,470 = 6,372,961.61   (itemized names not in the April lake table)
```

This is a vintage miss, not a "close enough." Criterion 5 fired.

## C. Class-A refresh file `indiv26.zip` (fec.gov, Last-Modified 2026-08-16 15:50:15 GMT, 2,098,465,857 bytes)

Streamed locally; 30,632,248 itcont rows scanned; queued as `infra.ingest_ledger` **2314349** → `lake.fec_individual_contributions_2026` (pending). Filter for C00902668:

| measure | value |
|---|---:|
| rows | 14,436 |
| sum all | 5,605,190.00 |
| sum non-memo | 5,598,190.00 |
| sum 15+15E (itemized individual) | 5,563,495.00 |
| sum 22Y | 20,695.00 |
| distinct names | 4,340 |
| name+zip keys | 4,471 |
| min/max date | 2025-03-10 .. **2026-03-31** |
| MI 15+15E | 6,139 rows / 1,971,638.00 |
| out-of-state 15+15E | 8,179 rows / 3,591,857.00 |

OpenFEC Schedule A **by_state** MI = 1,971,334.36 (matches the refresh 15+15E MI slice to rounding). The itemization warehouse and today's bulk file agree with each other.

Refresh vs Form 3 itemized:

```
10,265,431.61 − 5,563,495.00 = 4,701,936.61
```

That residual is **published as itemized on Form 3 through 2026-07-15** but is **absent from the 2026-08-16 FEC bulk itcont and from OpenFEC Schedule A aggregates**. The public itemization feed is still the Q1-2026 filing window (same vintage as `lake.fec_senate_candidate_summary_2026` itemized 5,571,782.85).

## D. Unitemized remainder (cannot be person-listed)

```
individual_unitemized = 4,142,626.45
```

FEC law does not publish names below the itemization threshold. This is a named remainder, not a rounding error.

## E. PAC / committee transfers (not the individual donor base)

| source | amount | notes |
|---|---:|---|
| OpenFEC other_political_committee | 71,845.23 | Form 3 through 2026-07-15 |
| lake.fec_pac_to_candidate_2026 24K to S6MI00418 | 29,875 | stale vs Form 3 |
| OpenFEC transfers from authorized | 0.00 | no JFC / other authorized cmte |

## F. Independent expenditures (NOT his donor base)

OpenFEC schedule E by-candidate (de-duplicated; do not sum raw `independent_expenditure_2026.csv` — that file still carries amendments):

| spender | S/O | amount |
|---|---|---:|
| FIGHTING FOR MICHIGAN PAC C00919373 | S | 1,134,115.61 |
| NATIONAL NURSES UNITED FOR PATIENT PROTECTION C00490375 | S | 489,664.76 |
| COMMON DEFENSE ACTION FUND C00620021 | S | 289,664.76 |
| MOVEON.ORG POLITICAL ACTION C00341396 | S | 39,165.61 |
| UNITED DEMOCRACY PROJECT (UDP) C00799031 | O | 2,346,357.50 |

Raw IE csv (queued ledger **2314348**) inflates UDP oppose to ~20.1M if amendments are summed — **do not use the raw sum**.

## G. 2018 Michigan gubernatorial

Class-A `lake.mi_sos_cf_contribs` years = **2020–2025 only**, 0 rows for El-Sayed / cfr_com_id 518037. `lake.mi_sos_cf_receipts` has 3 late refund/misc rows 2020–2021 totaling **10,283.73** for ABDUL EL-SAYED FOR MICHIGAN (518037) — not a donor roster. Agency 7z `2018_mi_cfr.7z` HTTP **404**. Class-B `tap_mi_contribs` holds 2018 but is **not mined**.

## Verdict on "exact"

A **named-person-complete** reconstruction is **not** possible:

1. Unitemized **4,142,626.45** has no names.
2. Form 3 itemized **4,701,936.61** is not yet in the public itemization files (bulk + OpenFEC aggregates) as of 2026-08-16.
3. There is no persistent FEC person id; 4,340 names / 4,471 name+zip keys are **not** unique persons.

The exact disclosed product is: **itemized roster from Class-A itcont through 2026-03-31 (5,563,495.00 / 14,436 rows) + quantified unitemized remainder + quantified Form-3-itemized-not-yet-in-bulk residual + separately labeled IE/super-PAC layer**.
