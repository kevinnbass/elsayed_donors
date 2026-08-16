"""Tighten NPPES physician floor: unique/all-physician only. Persist."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

OUT = Path(r"C:\Users\Kevin\hhs_doge\outputs\el_sayed_donor_base")
rows = []
with open(OUT / "nppes_donor_matches.jsonl", encoding="utf-8") as f:
    for line in f:
        rows.append(json.loads(line))

tot = sum(r["amt"] for r in rows)
# nppes_verdict values from adjudicate()
CONFIRMED_V = {"confirmed_physician", "all_hits_physician_ambiguous"}
MIXED_V = {"mixed_hits_some_physician"}

tight = defaultdict(lambda: {"n_donors": 0, "n_gifts": 0, "amt": 0.0, "sample": []})
for r in rows:
    fec_p = r.get("fec_physician_occ")
    v = r.get("nppes_verdict")
    nppes_conf = v in CONFIRMED_V
    nppes_mixed = v in MIXED_V
    if nppes_conf and fec_p:
        lab = "confirmed_both"
    elif nppes_conf and not fec_p:
        lab = "confirmed_nppes_fec_silent"
    elif nppes_mixed:
        lab = "mixed_homonym_not_in_floor"
    elif fec_p and v == "confirmed_nonphysician":
        lab = "dropped_fec_physician_unique_nonmd"
    elif fec_p and v == "unmatched":
        lab = "fec_physician_unmatched"
    elif fec_p:
        lab = "fec_physician_other"
    else:
        lab = "not_physician"
    b = tight[lab]
    b["n_donors"] += 1
    b["n_gifts"] += r.get("n_gifts") or 0
    b["amt"] += r["amt"]
    if len(b["sample"]) < 8:
        b["sample"].append({
            "name": r["name"], "state": r["state"], "amt": r["amt"],
            "occupations": r.get("occupations"), "verdict": v,
            "taxonomies": r.get("taxonomies"), "n_npi": r.get("n_npi"),
        })

floor = tight["confirmed_both"]["amt"] + tight["confirmed_nppes_fec_silent"]["amt"]
upper = (
    floor
    + tight["fec_physician_unmatched"]["amt"]
    + tight["fec_physician_other"]["amt"]
    + tight["mixed_homonym_not_in_floor"]["amt"]
)
out = {
    "named_itemized_total": round(tot, 2),
    "n_donors": len(rows),
    "nppes_confirmed_physician_floor_dollars": round(floor, 2),
    "nppes_confirmed_physician_floor_pct": round(100.0 * floor / tot, 2),
    "upper_bound_dollars": round(upper, 2),
    "upper_bound_pct": round(100.0 * upper / tot, 2),
    "rule": (
        "Floor = unique NPPES individual with taxonomy 207/208, or every "
        "same-name+state NPI is 207/208. Mixed homonyms are NOT in the floor."
    ),
    "buckets": {
        k: {
            "n_donors": v["n_donors"],
            "n_gifts": v["n_gifts"],
            "amt": round(v["amt"], 2),
            "pct": round(100.0 * v["amt"] / tot, 2),
            "sample": v["sample"],
        }
        for k, v in sorted(tight.items(), key=lambda kv: -kv[1]["amt"])
    },
}
(OUT / "healthcare_share_nppes_tight.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8"
)
print(json.dumps({k: out[k] for k in out if k != "buckets"}, indent=2))
print("buckets")
for k, v in out["buckets"].items():
    print(f"  {k}: ${v['amt']:,.2f} {v['pct']}% donors={v['n_donors']}")
print("WROTE healthcare_share_nppes_tight.json")

# README
(OUT / "README.md").write_text(
    """# El-Sayed donor-base analysis store

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
""",
    encoding="utf-8",
)
print("WROTE README.md")
