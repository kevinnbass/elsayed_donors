# El-Sayed 2026 donor-base analysis

Standalone reconstruction of **Abdul El-Sayed** / **ABDUL FOR U.S. SENATE** (`S6MI00418` / `C00902668`) from Class-A FEC electronic filings.

Named itemized money only unless noted. Unitemized gifts have no names or jobs.

## Time period

**January 1, 2025 through September 30, 2026** (cycle through the October quarterly report, filed Oct 15, 2026). Until Oct 16, 2026 this repo stopped at the July 15 pre-primary report; those figures are in git history (commit `7acb954`).

| Filing window | Filing | Named itemized $ |
|---|---|---:|
| Jan 1 – Jun 30, 2025 | 2005714 | 1.35M |
| Jul 1 – Sep 30, 2025 | 2005716 | 1.35M |
| Oct 1 – Dec 31, 2025 | 2005717 | 1.19M |
| Jan 1 – Mar 31, 2026 | 2005719 | 1.68M |
| Apr 1 – Jun 30, 2026 | 2026985 (amended Oct 15; was 2005720) | 3.30M |
| Jul 1 – 15, 2026 (pre-primary) | 2027035 (amended Oct 15; was 2005721) | 1.39M |
| Jul 16 – Sep 30, 2026 (October quarterly) | 2027095 | **14.01M** |

The two superseded filings are kept in `data/filings/superseded/` and are not read.

## Headline dollars

- Form 3 receipts, cycle to date: **$45,175,288.29**
- Named itemized individual: **$24,278,061.59** (104,093 gifts). Each report's rows add up exactly to its own line 11a(i). The committee's year-to-date column says $24,276,423.92, $1,637.67 lower: its running total has drifted from the sum of its own reports since Q3 2025 ($50 then, $552.40 at year-end 2025).
- Unitemized (no names): **$15,390,199.35**
- Joint fundraising transfers (Abdul for Michigan Victory Fund, `C00958066`), new in the October report: **$4,953,348.11**. Its memo entries attribute $4,989,800.69 to 3,769 named individual entries. That money is on line 12, not 11a(i), so it is outside the named itemized figures above and the shares below, but it is in each donor's net total (it counts toward their limit).
- $75,821.09 (963 gifts) of the October report's itemized money was given for the eventual Democratic nominee, dated as early as February 2025 and held under FEC Advisory Opinions 1977-16 and 1982-23 until El-Sayed won the Aug 4 primary. The month chart shows it on its original dates.

## Ranked occupation sectors (share of the $24.28M named)

1. **Not employed / retired / homemaker — 40.1% ($9.74M)** — “Not Employed” $8.15M · retired $1.41M · homemaker $0.14M (tighter cut without students: **$9.71M**)
2. **Healthcare — 19.2% ($4.67M)** — physicians $3.55M · other clinicians $0.77M · hospital/staff $0.36M
3. **Business owners / executives / consultants — 12.5% ($3.03M)**
4. **Unclassified / other titles — 6.8% ($1.66M)**
5. **Tech / engineering — 5.9% ($1.42M)**
6. **Law — 4.9% ($1.19M)**
7. **Media / sales / real estate / arts — 3.4% ($836k)**
8. **Finance — 3.1% ($760k)**
9. **Education — 2.8% ($687k)**
10. **Government / politics / nonprofit — 0.6% ($145k)**
11. **No occupation given (“Information Requested”, blank) — 0.5% ($131k)**

NPPES-confirmed MDs (unique last+first+state, taxonomy 207/208): **14.2%** floor ($3.44M) / **19.7%** upper bound ($4.79M) of named money. Through July 15 it was 20.1% / 27.1%: the $14.0M July–September quarter came from a broader base, with “Not employed / retired / homemaker” rising from 25.5% to 40.1% of named dollars and healthcare falling from 28.8% to 19.2%.

Sector shares are of gross named receipts (reconciles to Form 3). Refunds and reattributions are under 1% of that.

Machine-readable: `analysis/sector_breakdown.json`, `analysis/healthcare_share_nppes_tight.json` (re-run `scripts/nppes_share.py` in the hhs_doge venv; it needs `lake.nppes_full`).

### Sector rules (Oct 16, 2026)

The first rules matched short tokens inside words and applied physician titles to employer names, so “Nonprofit” counted as tech (`IT`), “Contractor” as media (`ACTOR`), anyone at an employer containing “Eastern”/“Northern” as a nurse (`RN`), “Engineer, AMD” and “Graduate Student, University of Toledo” as physicians (`MD`, `DO`), “Physician Assistant” as a physician and “Hospitality” as hospital staff. `scripts/sector_breakdown.py` now:

- matches short tokens as whole words;
- decides physician from the occupation only (assistants, technologists, dentists, pharmacists excluded); an employer can only place someone in hospital/system staff, and never overrides “Not employed / Retired”;
- reads the employer box when it holds the title and the occupation box does not (“Sutter” / “Physician”);
- adds titles the rules missed (physician misspellings, musician, realtor, police, nonprofit, COO/CTO, …), which took unclassified from 12.3% to 6.3% on the July data.

On the July data, $830k of $10.27M changed sector (healthcare 28.4% → 28.8%). Spot checks are in `tests/test_totals.py::test_sector_rules`.

## Name-origin shares of the $24.28M named (Oct 17, 2026 pass)

These are **name origins**, not a religion or race census. A name counts as **Arab-or-Muslim-coded** when either the surname or the given name is Arabic-language (any religion: Arab Christian, Coptic and Druze families count), Persian, Turkish, South Asian Muslim, Afghan, Somali / East or West African Muslim, Balkan Muslim or Southeast Asian Muslim. Assyrian/Chaldean Aramaic-origin, Armenian, Jewish, Hindu/Sikh and European names do not.

| Cut | Share of named $ |
|---|---:|
| **Arab-or-Muslim-coded, expected** | **45.2%** (range 44.4–45.9%) |
| of which confidently classified | 43.4% |
| still uncertain | 2.2% |
| Share of gifts (count) | 23.9% |
| Through Jul 15 / Jul 16 – Sep 30 | 71.2% / 25.8% |
| Michigan / outside Michigan | 41.6% / 46.7% |

By origin (share of all named $): Arabic 32.4% · South Asian Muslim 10.3% · Persian 0.6% · Turkish 0.3% · Afghan, Balkan and other Muslim 0.2% · uncertain residual 1.4%. The other 54.8%: English/Celtic 26.0% · Germanic 12.1% · Jewish 5.2% · Romance 3.0% · Slavic/Baltic/Hungarian 2.0% · South Asian non-Muslim 1.3% · Hispanic 1.0% · East Asian 0.9% · smaller groups the rest.

By donor (net totals, incl. joint-committee shares): 33.5% of the 30,726 donors, carrying 51.2% of net dollars; 76.3% of the 644 who gave the $7,000 maximum; 79.5% of the dollars from the 2,072 donors who gave only through the joint fundraising committee.

**Method.**
- Every distinct surname (16,502) and given name (6,063) in the donor file was labelled with an origin and a probability, one judgment per name, using the names it appears with and the donors' states as context (rubric: `analysis/name_lexicon/RUBRIC.md`; lexicon: `surnames.jsonl`, `given.jsonl`). Labels were made by Claude Sonnet in 20 batches.
- **Validated** before use against an independent gold set built from Wikipedia's language-of-name categories ("Arabic-language surnames", "English-language surnames", "Hebrew masculine given names", …): on the 3,669 gold surnames in this donor file, recall 0.99, precision 0.91, AUC 0.999; on 2,072 gold given names, recall 0.99, precision 0.96, AUC 0.995. Most "errors" are names the gold set files under one tradition that are Muslim among these donors (Malik, Shah, Adel, Sana); names given p 0.8–1.0 are truly Arab-or-Muslim-coded 95–98% of the time.
- **Second engine:** Codex (GPT-6.1 Sol) labelled a stratified sample of 400 names blind: 91.7% agreement, Cohen's kappa 0.84 (100% on confident names, 79% on mid-probability ones, where Codex runs higher; using its calibration would move the headline about +0.5 points).
- The 1,183 full names whose two halves left them uncertain (3.8% of $; e.g. a shared surname like Shah with Anup vs with Syed) were judged as pairs with city/state; those per-donor judgments stay out of the repo (`analysis/private/`, gitignored). Two final-pass overrides with reasons: `analysis/name_lexicon/audit_overrides.jsonl`. Initials are treated as uninformative.
- Range: the low end treats a name as coded only through its stronger half; the high end treats the halves as independent evidence.

Re-run: `python scripts/name_origin_share.py` → `analysis/name_origin_share.json` (aggregates only).

**Superseded:** the token-list method (`muslim_name_share.py`, `nonwhite_name_share.py`, `name_share_recall.py`), kept for history. Its lists were curated on the July data: 69.5% through Jul 15 (11.9% unclassified), but only 40.3% with 34.5% unclassified on the full cycle. It also produced false positives from its Al-/El- prefix rule (Albright, Elfstrom, Altschuler, …: $152k) and missed $1.22M of Arabic and South Asian Muslim names (Ansara, Ezzeddin, Samhat, Hadeed, Makhdoom, Begum, …).

## Figures

`figures/elsayed_ledger.html` — self-contained interactive dashboard (open in any browser): monthly deadline dynamics, gift-size vs dollar shares, donor concentration, geography, sectors, employers, and the name-token cuts with a ≈2% U.S.-population reference. Aggregates feeding it: `analysis/figure_aggregates.json` (re-run `python scripts/figure_aggregates.py`).

## Donor lists (copy-paste)

Every list is **net of refunds and reattributions** and includes joint-committee shares. The limit is $7,000 per person ($3,500 primary + $3,500 general) and **644 donors gave it**, so a ranked top 20 or top 100 is a tie; the lists show everyone at the maximum instead.

- **Top 100 and every sector:** [`analysis/TOP100_and_by_sector.txt`](analysis/TOP100_and_by_sector.txt) — 100 drawn at random from the 644 (fixed seed, re-runnable), the 32 still above $7,000, then each sector's donors at the maximum (or its top 20 where fewer than 20 reached it). Names only: [`analysis/TOP100_names.txt`](analysis/TOP100_names.txt)
- Physicians and health employers: [`analysis/TOP20.txt`](analysis/TOP20.txt) — all 117 NPPES-confirmed physicians at the maximum (100 whose FEC occupation also says physician, 17 name-match only), and the top 20 employers of health-care donors
- Not employed / retired / homemaker: [`analysis/TOP20_not_employed.txt`](analysis/TOP20_not_employed.txt) — all 153 at the maximum

`python scripts/report.py` reprints the physician and employer lists from local files.

### Net donor totals (Oct 16, 2026)

The first physician and not-employed lists added up gross Schedule A gifts. That overstated the people at the top: an excess gift stays on Schedule A while its fix is a refund (SB20A) or a memo reattribution to a spouse. Issa, Said showed $14,500; net he is $7,000 (plus a different Said Issa at another Ann Arbor address, $2,000). Barakat, Abdul $14,000 → $7,000. The dashboard's July "78 donors above $7,000, max $14.5k" was the same artifact.

`scripts/top_donors.py` builds per-donor net totals (`analysis/donors_net.jsonl`), keyed by name + suffix + ZIP + house number (the same name at another ZIP or house number is not merged, so a mover splits rather than two people merging):

- net = itemized gifts + the committee's memo reattributions/redesignations + joint-committee shares − SB20A refunds. 30,726 donors, $29,089,348.78, of which $4,989,800.69 came through the joint committee; 2,074 donors gave only that way.
- 32 donors stand above $7,000 (max $10,500) in the committee's own running totals as of the Sep 30 report (refunds of an excess can come in a later report).
- Check against the committee's own per-donor aggregate: 21,872 exact, 8,705 within $200 (early gifts under the itemization line), 149 differ (0.5%; movers split across ZIPs or house numbers, and people the committee keeps as two records). None of the 32 above $7,000 differs. A joint-committee row's aggregate is sometimes the donor's combined total and sometimes the joint committee's own, so donors with both kinds of money are checked against both readings.
- Sector = the occupation carrying most of a donor's dollars, using the `sector_breakdown.py` rules.
- Top 100: the 644 at or above $7,000 are ordered by sha256 of `elsayed-top100-2026-10-16|last|first|suffix|zip5|house` and the first 100 taken.
- Three refunds went to companies (a corporate gift is not allowed); they and the ten corporate gifts ($27,245) are outside the individual totals.

Run order after a data change: `build_roster.py` → `nppes_share.py` (hhs_doge venv) → `sector_breakdown.py` → `top_donors.py` → `format_top20.py`, `top20_not_employed.py`, `figure_aggregates.py`, `muslim_name_share.py`, `nonwhite_name_share.py`, `name_share_recall.py`, `sdn_screen.py <SDN dir> <candidates out>`. Per-donor figures in the dashboard (donor counts, size brackets, concentration, employers) use net totals; gift-level figures (months, gift sizes, states, sectors) use the roster as filed.

Machine-readable: `analysis/top_donors.json`, `analysis/donors_net.jsonl`, `analysis/sdn_screen.json` (OFAC SDN screen of every donor: no corroborated matches).

Published-claims check (outputs private): `mb_claims_screen.py <corpus>` → claim extraction → `mb_claims_build.py <corpus> analysis/private/mb_claims` → `mb_verdicts_assemble.py <lanes> <evidence store>` → `mb_claims_build.py` again → `mb_claims_summary.py analysis/private/mb_claims`. It archives every story found that ties El-Sayed's family, donors, super PACs or endorsers to the Muslim Brotherhood or terror-linked groups, extracts each claim with a verbatim quote and every link, matches named people to FEC records as candidates, and judges each distinct claimed tie against primary records (court records, government designations, tax filings, FEC filings, the organizations' own pages). The tables name individuals and repeat allegations about them, so they stay in the gitignored `analysis/private/`.

## Layout

```
analysis/                  totals, NPPES matches, net donor totals and lists, sector ranking
data/filings/              most-recent version of each F3 report, .csv / .fec (the named-roster source)
data/filings/superseded/   earlier versions replaced by amendments (kept, not read)
scripts/                   build_roster.py, analysis scripts, report.py (no database) + archived rematch scripts
```

## What is not here

- The 2.1 GB `indiv26.zip` (FEC bulk was stale through Q1 2026). E-files are the source of truth.
- Super-PAC / IE money is not this donor base.
- 2018 Michigan gubernatorial itemized names: no Class-A 2017–2019 SOS bulk.

## Legal

FEC electronic filings are Class-A government records. Occupation/employer are self-reported. Last+first+state NPPES match is inference, not identity.
