# Abdul El-Sayed disclosed political donor base (Class-A reconstruction)

Reconstructed 2026-08-16 from the live `hhs_doge` PostgreSQL lake plus a same-day Class-A FEC bulk refresh. Not a unique-person census. Every headline number below is also in `el_sayed_recon.out`.

**Verdict:** a **named-person-complete** reconstruction is **NO**. Unitemized dollars have no names; FEC has no persistent donor id; and 4,701,936.61 of Form 3 "itemized" through 2026-07-15 is not yet in the public itemization files.

---

## 1. Committee universe (Class-A lake)

Source: `lake.fec_candidate_master_2026`, `lake.fec_committee_master_2026`, `lake.fec_candidate_committee_linkages_2026`.

| role | id | name | designation / type | source table | coverage |
|---|---|---|---|---|---|
| Senate candidate | **S6MI00418** | EL-SAYED, ABDUL | DEM / MI / S / status C | fec_candidate_master_2026 | 2026 cycle file |
| Authorized PCC (donor base) | **C00902668** | ABDUL FOR U.S. SENATE | P / S / DEM / ST CLAIR SHORES MI | fec_committee_master_2026 | only linkage (linkage_id 264188) |
| Independent spender — **NOT donor base** | **C00919373** | FIGHTING FOR MICHIGAN PAC | U / O / unauthorized / Silver Spring MD | fec_committee_master_2026 | no cand_id; not a linkage |
| 2018 MI governor committee | **518037** | ABDUL EL-SAYED FOR MICHIGAN | GUB | mi_sos_cf_receipts only | 2020–2021 remnant, not 2018 roster |

No other authorized or affiliated FEC committee is linked to S6MI00418. OpenFEC `transfers_from_other_authorized_committee` = **0.0**. Candidate contribution on the live Form 3 = **0.0**.

---

## 2. Itemized donor-base rollup (authorized PCC only)

**Warehouse used:** FEC bulk `indiv26.zip` Last-Modified **2026-08-16T15:50:15Z** (2,098,465,857 bytes), 30,632,248 itcont rows scanned. Filter `cmte_id=C00902668`. Queued to `lake.fec_individual_contributions_2026` as ingest_ledger **2314349**.

Lake `fec_itcont_2026` is an older slice of the same family (8,344 rows / 3,892,470 itemized through 2025-12-31) and is superseded for the roster by the refresh file.

### 2.1 Headline (refresh file)

| measure | value |
|---|---:|
| itemized rows | 14,436 |
| 15+15E itemized individual $ | **5,563,495.00** |
| 22Y refunds (positive in file; not added to donor $) | 20,695.00 |
| distinct `name` strings | 4,340 |
| distinct name+zip keys | 4,471 |
| contribution dates | 2025-03-10 .. 2026-03-31 |
| earmark / ActBlue-class rows (15E or ACTBLUE memo) | 13,561 |

Conduit/memo is preserved as a field. ActBlue is **not** treated as the true donor. Memo_cd=`X` rows are excluded from dollars.

Same-name rows are **not** unique persons. 4,340 names vs 4,471 name+zip keys is the homonym / multi-zip residue; there is no FEC person id.

### 2.2 Geography (15+15E)

| | n | $ |
|---|---:|---:|
| Michigan | 6,139 | 1,971,638.00 |
| Out of state | 8,179 | 3,591,857.00 |
| OpenFEC by_state MI (warehouse check) | 6,172 | 1,971,334.36 |

MI is about **35%** of itemized dollars in the warehouse (`1,971,638 / 5,563,495`). The rest is national, led by CA (2,130 / 1,211,541), NY (779 / 365,446), IL (564 / 306,124), TX (412 / 254,311), VA (332 / 203,294).

### 2.3 Amount bands (15+15E, refresh)

| band | n | $ |
|---|---:|---:|
| <200 | 9,520 | 394,060.00 |
| 200–999 | 2,850 | 1,069,241.00 |
| 1,000–2,799 | 1,285 | 1,786,967.00 |
| 2,800–3,600 | 656 | 2,266,627.00 |
| >3,600 | 7 | 46,600.00 |

Most **rows** are small; most **dollars** sit at or near the cycle limit.

### 2.4 Employer / occupation (OpenFEC Schedule A aggregates — same warehouse vintage)

Occupation $: PHYSICIAN 1,236,053.67 · NOT EMPLOYED 1,029,175.67 · ATTORNEY 278,974.39 · RETIRED 213,093.72 · CEO 180,334.00 · ENGINEER 157,967.06.

Employer $: NOT EMPLOYED 1,235,864.39 · SELF EMPLOYED 795,551.31 · HENRY FORD HEALTH 58,170.00 · UNIVERSITY OF MICHIGAN 40,644.80 · GOOGLE 33,095.00 · COREWELL HEALTH 31,430.00 · APPLE 31,000.00.

These aggregates match the Q1 itemization warehouse, not the July Form 3.

---

## 3. Unitemized remainder (cannot be person-listed)

OpenFEC / Form 3 through 2026-07-15:

```
individual_unitemized_contributions = 4,142,626.45
```

This is the legally unnamed remainder. It is **not** in the itemized roster and cannot be reconstructed from any Class-A public file.

---

## 4. Form 3 vs itemization-warehouse residual

| | $ |
|---|---:|
| Form 3 individual itemized through 2026-07-15 | 10,265,431.61 |
| Refresh itcont 15+15E through 2026-03-31 | 5,563,495.00 |
| **Itemized names not yet in bulk/API warehouse** | **4,701,936.61** |
| Form 3 total individual | 14,408,058.06 |
| Form 3 receipts | 14,514,335.93 |

`lake.fec_senate_candidate_summary_2026` still shows the stale Q1 snapshot (coverage_end 2026-03-31, receipts 7,646,727.83, itemized 5,571,782.85) — consistent with the warehouse, not with the July Form 3.

---

## 5. Independent-expenditure / super-PAC layer (labeled separately)

**Not his donor base.** Money is spent *about* him, or donated *to* an unauthorized committee.

Fighting for Michigan PAC **C00919373** (U/O): 40 itcont rows totaling 2,467,250.00 received (refresh file); OpenFEC IE **support** 1,134,115.61.

Other OpenFEC schedule E by-candidate (de-duplicated):

- Support: NNU 489,664.76 · Common Defense 289,664.76 · MoveOn 39,165.61
- Oppose: United Democracy Project (UDP) **2,346,357.50**

Raw `independent_expenditure_2026.csv` (queued ledger **2314348**) still contains amendments; a naive sum puts UDP oppose near 20.1M. Use OpenFEC by-candidate or de-dup, never the raw csv total.

---

## 6. 2018 Michigan gubernatorial layer

Class-A `lake.mi_sos_cf_contribs` (6,468,956 rows) covers **2020–2025 only**. Cross-schema sweep found no other Class-A 2018 MI CF table. Search by `can_last_name` EL-SAYED / `cfr_com_id` 518037 / `com_legal_name` ABDUL EL-SAYED: **0 contribution rows**.

`lake.mi_sos_cf_receipts` has **3** late rows for ABDUL EL-SAYED FOR MICHIGAN (518037, GUB, first name misspelled ADBULRAHMAN): refund/rebate 2020 7,159.03 + misc 2021 3,124.70 = **10,283.73**. That is not a 2018 donor roster.

Agency-direct 7z `https://www.michigan.gov/sos/-/media/Project/Websites/sos/Elections/Disclosure/MiTN/Legacy-Data/2018_mi_cfr.7z` → HTTP **404** (same for 2016, 2017, 2019). 2020–2025 7z files are 200 and already ingested.

Class-B `lake.tap_mi_contribs` (legal_class B) holds 2018 (1,855,270 rows) and was **not mined**. No Class-A drain of a 404 URL was built.

---

## 7. What was queued (no second ingest worker)

| ledger_id | target | source | status |
|---|---|---|---|
| 2314349 | fec_individual_contributions_2026 | https://www.fec.gov/files/bulk-downloads/2026/indiv26.zip | pending |
| 2314347 | fec_pac_to_candidate_2026 | https://www.fec.gov/files/bulk-downloads/2026/pas226.zip | pending |
| 2314348 | fec_independent_expenditures | https://www.fec.gov/files/bulk-downloads/2026/independent_expenditure_2026.csv | pending |

Targets are the documented per-cycle / existing 2026 FEC tables. **Never** `lake.itcont`, `drain_political_intel`, `queue_downloads_www_fec_gov`, or `by_date_itcont_2026_*`.

---

## 8. Do-not-use tables (inventory)

- `lake.itcont` — blacklisted; not in pg
- `lake.by_date_itcont_2026_*` — consolidated into `fec_itcont_2026`
- `lake.tap_mi_contribs` / `tap_mi_expends` / `tap_mi_lobby` — Class B
- `lake.dime_contribdb_consolidated` — Class B
- `lake.fec_pac_to_candidate` (no year) — scrambled columns; use `_2026`

---

## 9. Named-person-complete?

**NO.** Three independent holes:

1. Unitemized **4,142,626.45** — no names by law.
2. Form 3 itemized **4,701,936.61** not in the 2026-08-16 public itemization warehouse.
3. No persistent FEC donor id — 4,340 name strings are not unique persons.

The exact disclosed product is the itemized Class-A roster through 2026-03-31 plus those quantified remainders, with IE/super-PAC money kept off the donor-base ledger.

## 10. Raw headline tokens (same figures as `el_sayed_recon.out`)

14514335.93 14408058.06 10265431.61 4142626.45 71845.23 5563495.00 14436 4340 4471 1971638.00 4701936.61 8344 3892470 C00902668 S6MI00418 C00919373 2314349 10283.73
