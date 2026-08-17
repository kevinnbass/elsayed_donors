# El-Sayed 2026 donor-base analysis

Standalone reconstruction of **Abdul El-Sayed** / **ABDUL FOR U.S. SENATE** (`S6MI00418` / `C00902668`) from Class-A FEC electronic filings.

Named itemized money only unless noted. Unitemized gifts have no names or jobs.

## Time period

**January 1, 2025 through July 15, 2026** (cycle through the pre-primary report).

| Filing window | Named itemized $ |
|---|---:|
| Jan 1 – Jun 30, 2025 | 1.35M |
| Jul 1 – Sep 30, 2025 | 1.35M |
| Oct 1 – Dec 31, 2025 | 1.19M |
| Jan 1 – Mar 31, 2026 | 1.68M |
| Apr 1 – Jun 30, 2026 | 3.30M |
| Jul 1 – 15, 2026 (pre-primary) | 1.39M |

## Headline dollars

- Form 3 receipts: **$14,514,335.93**
- Named itemized individual: **$10,265,431.61** (31,180 gifts) — matches Form 3 line 11a(i)
- Unitemized (no names): **$4,142,626.45**

## Ranked occupation sectors (share of the $10.26M named)

1. **Healthcare — 28.4% ($2.92M)** — physicians $2.40M · other clinicians $0.40M · hospital/staff $0.12M
2. **Not employed / retired / homemaker — 25.3% ($2.60M)** — “Not Employed” $2.13M · retired $0.33M · homemaker $0.11M (tighter cut without students: **$2.58M**)
3. **Business owners / executives / consultants — 13.7% ($1.41M)**
4. **Unclassified / other titles — 12.3% ($1.26M)**
5. **Tech / engineering — 6.3% ($644k)**
6. **Law — 5.0% ($508k)**
7. **Finance — 3.5% ($358k)**
8. **Media / sales / real estate / arts — 3.0% ($305k)**
9. **Education — 2.2% ($226k)**
10. **Government / politics / nonprofit — 0.2%**

NPPES-confirmed MDs (unique last+first+state, taxonomy 207/208): **20%** floor / **27%** upper bound of named money.

Machine-readable: `analysis/sector_breakdown.json`

## Name-token shares of the $10.26M named

These are **name tokens**, not a religion or race census. Anglicized names, converts, and shared surnames (Ali, Khan, Hanna, Lee, Williams) cut both ways.

Headline cut is **Arab or Muslim**, not Muslim-only. Pakistani / Persian / Turkish Muslim names count. Levantine Christian surnames (Haddad, Khoury, Abdo, Chami, Dudum) count.

| Cut | $ | Share of named |
|---|---:|---:|
| **Arab or Muslim name** | **$6,638,797** | **64.7%** |
| Non-white-coded name (Arab/Muslim + Hispanic + South/East Asian) | $6,868,754 | **66.9%** |
| Clearly Anglo / White-coded surname | $1,241,507 | 12.1% |
| Ambiguous leftover (not counted as non-white) | $2,136,620 | 20.8% |

A first-pass **Muslim-only** list was 49%. After recall (Rasheed, Zaidi, Abdulhak, ABU- prefixes, …) that same Muslim-only cut was 63.1%. Adding Arab Christian / Levantine surnames moves the headline to **64.7%**. Top-20 donor lists are ~85% Arab-or-Muslim-named because the top is concentrated; those top 100 people are only ~9% of all named dollars.

The non-white figure is the Arab-or-Muslim figure plus:

- South Asian surnames not already in that cut: **1.1%** ($110k)
- East / Southeast Asian surnames: **0.6%** ($66k)
- Hispanic / Latino surnames: **0.5%** ($47k)

Machine-readable: `analysis/muslim_name_share.json`, `analysis/nonwhite_name_share.json`. Re-run: `python scripts/muslim_name_share.py` then `python scripts/nonwhite_name_share.py`.

### Recall pass over the ambiguous bucket (Aug 16, 2026)

`scripts/name_share_recall.py` reclassifies the 20.8% ambiguous leftover with ~450 additional surname tokens curated from its top surnames by dollars, **on both sides** (Bazzi, Itani, Iqbal, … and Griswold, Costello, Katz, …), plus a distinctive-given-name list for the tail. Recovery applies only to base-ambiguous rows. Updated cuts (supersede the table above):

| Cut | $ | Share of named |
|---|---:|---:|
| **Arab or Muslim name** | **$7,133,411** | **69.5%** |
| Non-white-coded name | $7,404,959 | **72.1%** |
| Clearly Anglo / White-coded surname | $1,623,339 | 15.8% |
| Ambiguous remaining | $1,218,584 | 11.9% |

Remaining ambiguity is 12,214 mostly small gifts (avg ~$100) — Western given names with uncommon surnames. Machine-readable: `analysis/name_share_recall.json`.

## Figures

`figures/elsayed_ledger.html` — self-contained interactive dashboard (open in any browser): monthly deadline dynamics, gift-size vs dollar shares, donor concentration, geography, sectors, employers, and the name-token cuts with a ≈2% U.S.-population reference. Aggregates feeding it: `analysis/figure_aggregates.json` (re-run `python scripts/figure_aggregates.py`).

## Top-20 lists (copy-paste)

- Physicians and health-system employers: [`analysis/TOP20.txt`](analysis/TOP20.txt)
- Not employed / retired / homemaker: [`analysis/TOP20_not_employed.txt`](analysis/TOP20_not_employed.txt)

`python scripts/report.py` reprints the physician and system lists from local files.

## Layout

```
analysis/          totals, NPPES matches, top-20 lists, sector ranking
data/filings/      most-recent F3 .csv / .fec (the named-roster source)
scripts/           report.py (no database) + archived rematch scripts
```

## What is not here

- The 2.1 GB `indiv26.zip` (FEC bulk was stale through Q1 2026). E-files are the source of truth.
- Super-PAC / IE money is not this donor base.
- 2018 Michigan gubernatorial itemized names: no Class-A 2017–2019 SOS bulk.

## Legal

FEC electronic filings are Class-A government records. Occupation/employer are self-reported. Last+first+state NPPES match is inference, not identity.
