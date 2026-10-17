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

1. **Healthcare — 28.8% ($2.95M)** — physicians $2.38M · other clinicians $0.41M · hospital/staff $0.17M
2. **Not employed / retired / homemaker — 25.5% ($2.62M)** — “Not Employed” $2.13M · retired $0.33M · homemaker $0.13M (tighter cut without students: **$2.60M**)
3. **Business owners / executives / consultants — 16.4% ($1.69M)**
4. **Tech / engineering — 6.5% ($670k)**
5. **Unclassified / other titles — 6.3% ($645k)**
6. **Law — 5.0% ($511k)**
7. **Finance — 3.9% ($398k)**
8. **Media / sales / real estate / arts — 3.8% ($394k)**
9. **Education — 2.3% ($241k)**
10. **Government / politics / nonprofit — 0.8% ($77k)**
11. **No occupation given (“Information Requested”, blank) — 0.7% ($74k)**

NPPES-confirmed MDs (unique last+first+state, taxonomy 207/208): **20%** floor / **27%** upper bound of named money.

Sector shares are of gross named receipts (reconciles to Form 3). Refunds and reattributions are 0.7% of that, so netting cannot move any share by more than 0.7 points.

Machine-readable: `analysis/sector_breakdown.json`

### Sector rules (Oct 16, 2026)

The first rules matched short tokens inside words and applied physician titles to employer names, so “Nonprofit” counted as tech (`IT`), “Contractor” as media (`ACTOR`), anyone at an employer containing “Eastern”/“Northern” as a nurse (`RN`), “Engineer, AMD” and “Graduate Student, University of Toledo” as physicians (`MD`, `DO`), “Physician Assistant” as a physician and “Hospitality” as hospital staff. `scripts/sector_breakdown.py` now:

- matches short tokens as whole words;
- decides physician from the occupation only (assistants, technologists, dentists, pharmacists excluded); an employer can only place someone in hospital/system staff, and never overrides “Not employed / Retired”;
- reads the employer box when it holds the title and the occupation box does not (“Sutter” / “Physician”);
- adds titles the rules missed (physician misspellings, musician, realtor, police, nonprofit, COO/CTO, …), which takes unclassified from 12.3% to 6.3%.

$830k of $10.27M changed sector. Healthcare 28.4% → 28.8%; physicians $2.40M → $2.38M. Spot checks are in `tests/test_totals.py::test_sector_rules`.

## Name-token shares of the $10.26M named

These are **name tokens**, not a religion or race census. Anglicized names, converts, and shared surnames (Ali, Khan, Hanna, Lee, Williams) cut both ways.

Headline cut is **Arab or Muslim**, not Muslim-only. Pakistani / Persian / Turkish Muslim names count. Levantine Christian surnames (Haddad, Khoury, Abdo, Chami, Dudum) count.

| Cut | $ | Share of named |
|---|---:|---:|
| **Arab or Muslim name** | **$6,638,797** | **64.7%** |
| Non-white-coded name (Arab/Muslim + Hispanic + South/East Asian) | $6,868,754 | **66.9%** |
| Clearly Anglo / White-coded surname | $1,241,507 | 12.1% |
| Ambiguous leftover (not counted as non-white) | $2,136,620 | 20.8% |

A first-pass **Muslim-only** list was 49%. After recall (Rasheed, Zaidi, Abdulhak, ABU- prefixes, …) that same Muslim-only cut was 63.1%. Adding Arab Christian / Levantine surnames moves the headline to **64.7%**. The 446 donors at the $7,000 maximum are 86% Arab-or-Muslim-named because the top is concentrated, but they hold only 31% of named dollars (net); the base-wide share is not a top-donor artifact (`name_share_recall.json` → `by_donor_tier`).

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

## Donor lists (copy-paste)

Every list is **net of refunds and reattributions**. The limit is $7,000 per person ($3,500 primary + $3,500 general) and **446 donors gave it**, so a ranked top 20 or top 100 is a tie; the lists show everyone at the maximum instead.

- **Top 100 and every sector:** [`analysis/TOP100_and_by_sector.txt`](analysis/TOP100_and_by_sector.txt) — 100 drawn at random from the 446 (fixed seed, re-runnable), the 24 still above $7,000, then each sector's donors at the maximum (or its top 20 where fewer than 20 reached it)
- Physicians and health employers: [`analysis/TOP20.txt`](analysis/TOP20.txt) — all 86 NPPES-confirmed physicians at the maximum (71 whose FEC occupation also says physician, 15 name-match only), and the top 20 employers of health-care donors
- Not employed / retired / homemaker: [`analysis/TOP20_not_employed.txt`](analysis/TOP20_not_employed.txt) — all 101 at the maximum

`python scripts/report.py` reprints the physician and employer lists from local files.

### Net donor totals (Oct 16, 2026)

The first physician and not-employed lists added up gross Schedule A gifts. That overstated the people at the top: an excess gift stays on Schedule A while its fix is a refund (SB20A) or a memo reattribution to a spouse. Issa, Said showed $14,500; net he is $7,000 (plus a different Said Issa at another Ann Arbor address, $2,000). Barakat, Abdul $14,000 → $7,000. The dashboard's "78 donors above $7,000, max $14.5k" was the same artifact: net, it is 24, max $10.5k.

`scripts/top_donors.py` builds per-donor net totals (`analysis/donors_net.jsonl`), keyed by name + suffix + ZIP (same name at another ZIP is not merged):

- net = itemized gifts + the committee's memo reattributions/redesignations − SB20A refunds. 8,528 donors, $10,195,699.46.
- 24 donors stand above $7,000 in the committee's own running totals as of the Jul 15 report (refunds of an excess can come in a later report).
- Check against the committee's own per-donor aggregate: 5,514 exact, 2,992 within $200 (early gifts under the itemization line), 22 differ (mostly one person the committee keeps as two records).
- Sector = the occupation carrying most of a donor's dollars, using the `sector_breakdown.py` rules.
- Top 100: the 446 at or above $7,000 are ordered by sha256 of `elsayed-top100-2026-10-16|last|first|suffix|zip5` and the first 100 taken.

Run order after a data change: `top_donors.py` → `format_top20.py`, `top20_not_employed.py`, `figure_aggregates.py`, `name_share_recall.py`. Per-donor figures in the dashboard (donor counts, size brackets, concentration, employers) use net totals; gift-level figures (months, gift sizes, states, sectors) use the roster as filed.

Machine-readable: `analysis/top_donors.json`, `analysis/donors_net.jsonl`.

## Layout

```
analysis/          totals, NPPES matches, net donor totals and lists, sector ranking
data/filings/      most-recent F3 .csv / .fec (the named-roster source)
scripts/           report.py (no database) + archived rematch scripts
```

## What is not here

- The 2.1 GB `indiv26.zip` (FEC bulk was stale through Q1 2026). E-files are the source of truth.
- Super-PAC / IE money is not this donor base.
- 2018 Michigan gubernatorial itemized names: no Class-A 2017–2019 SOS bulk.

## Legal

FEC electronic filings are Class-A government records. Occupation/employer are self-reported. Last+first+state NPPES match is inference, not identity.
