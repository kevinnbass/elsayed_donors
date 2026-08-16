# El-Sayed 2026 donor-base analysis

Standalone reconstruction of **Abdul El-Sayed** / **ABDUL FOR U.S. SENATE** (`S6MI00418` / `C00902668`) from Class-A FEC electronic filings. Moved out of `hhs_doge`.

This is **disclosed itemized money**, not a unique-person census. Unitemized gifts have no names.

## Bottom line (cycle through 2026-07-15)

- Form 3 receipts: **$14,514,335.93**
- Named itemized individual: **$10,265,431.61** (31,180 gifts) — matches Form 3 line 11a(i)
- Unitemized (no names): **$4,142,626.45**
- People who filed a physician/doctor/surgeon title: about **23%** of named money
- NPPES-confirmed MDs (unique last+first+state, taxonomy 207/208): **20%** floor / **27%** upper bound
- All healthcare titles (MDs + dentists, pharmacists, nurses, etc.): about **28%** of named money

Copy-paste lists: `analysis/TOP20.txt`

## Layout

```
analysis/          derived totals, NPPES matches, top-20 lists
data/filings/      most-recent F3 .csv / .fec (the named-roster source)
scripts/           report.py (no database) + archived hhs_doge rematch scripts
```

`python scripts/report.py` prints the share and top-20 lists from local files.

## What is not here

- The 2.1 GB `indiv26.zip` / 5.6 GB extracted itcont (still on `K:/drain/political/fec_2026_refresh/20260816/`). Bulk was stale through Q1 2026; the e-files are the source of truth.
- Super-PAC / IE money (Fighting for Michigan, UDP, etc.) is **not** this donor base.
- 2018 Michigan gubernatorial itemized names: no Class-A 2017–2019 SOS bulk on michigan.gov.

## Rematch against NPPES

`scripts/recompute/` still talks to the `hhs_doge` lake (`lake.nppes_full`). Only needed if you rebuild the join. The checked-in `analysis/nppes_donor_matches.jsonl` is the last run.

## Legal

FEC bulk and electronic filings are Class-A government records. Occupation/employer are self-reported. Last+first+state NPPES match is inference, not identity.
