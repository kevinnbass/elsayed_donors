"""Aggregate the named-itemized roster into figure-ready JSON.

Feeds the "El-Sayed Ledger" figures: monthly totals, gift-size and
donor-total brackets, state totals, top disclosed employers, and
per-donor concentration stats. Donor key is last+first+state, same as
the NPPES match. Writes analysis/figure_aggregates.json.
"""
import collections
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "figure_aggregates.json"

rows = []
with open(ROOT / "analysis" / "roster_named_itemized.jsonl", encoding="utf-8") as f:
    for line in f:
        rows.append(json.loads(line))

monthly = collections.defaultdict(lambda: [0.0, 0])
for r in rows:
    d = r.get("date") or ""
    if len(d) == 8 and d.isdigit():
        monthly[d[:6]][0] += r["amt"]
        monthly[d[:6]][1] += 1
monthly_out = [{"month": k, "amt": round(v[0], 2), "n": v[1]} for k, v in sorted(monthly.items())]

brackets = [(0, 25, "$1-25"), (25, 100, "$26-100"), (100, 250, "$101-250"),
            (250, 1000, "$251-1k"), (1000, 3500, "$1k-3.5k"), (3500, 10**9, "$3.5k+")]
br = {label: [0.0, 0] for _, _, label in brackets}
for r in rows:
    a = r["amt"]
    if a <= 0:
        continue  # 4 negative/zero rows (refund-style entries) stay out of brackets
    for lo, hi, label in brackets:
        if lo < a <= hi:
            br[label][0] += a
            br[label][1] += 1
            break
size_out = [{"bracket": label, "amt": round(v[0], 2), "n": v[1]} for label, v in br.items()]

states = collections.defaultdict(lambda: [0.0, 0])
for r in rows:
    st = (r.get("state") or "??").upper()
    states[st][0] += r["amt"]
    states[st][1] += 1
states_out = sorted(
    [{"state": k, "amt": round(v[0], 2), "n": v[1]} for k, v in states.items()],
    key=lambda x: -x["amt"])

donors = collections.defaultdict(lambda: [0.0, 0])
for r in rows:
    key = (r["last_norm"], r["first_norm"], (r.get("state") or "").upper())
    donors[key][0] += r["amt"]
    donors[key][1] += 1
totals = [v[0] for v in donors.values()]
gift_counts = [v[1] for v in donors.values()]
totals_sorted = sorted(totals, reverse=True)
grand = sum(totals)
donor_out = {
    "n_named_donors": len(donors),
    "median_donor_total": round(statistics.median(totals), 2),
    "mean_donor_total": round(grand / len(donors), 2),
    "repeat_donor_pct": round(sum(1 for c in gift_counts if c > 1) / len(donors) * 100, 1),
    "gifts_from_repeat_pct": round(sum(c for c in gift_counts if c > 1) / len(rows) * 100, 1),
    "donors_3500_plus": sum(1 for t in totals if t >= 3500),
    "donors_7000_plus": sum(1 for t in totals if t >= 7000),
    "donors_over_7000": sum(1 for t in totals if t > 7000),
    "max_donor_total": round(max(totals), 2),
    "top100_pct_of_named": round(sum(totals_sorted[:100]) / grand * 100, 1),
    "top1000_pct_of_named": round(sum(totals_sorted[:1000]) / grand * 100, 1),
    "median_gift": round(statistics.median(r["amt"] for r in rows), 2),
    "mean_gift": round(sum(r["amt"] for r in rows) / len(rows), 2),
}

dbrackets = [(0, 100, "$1-100"), (100, 500, "$101-500"), (500, 1000, "$501-1k"),
             (1000, 3500, "$1k-3.5k"), (3500, 7000, "$3.5k-7k"), (7000, 10**9, "$7k+")]
db = {label: [0.0, 0] for _, _, label in dbrackets}
for t in totals:
    if t <= 0:
        continue
    for lo, hi, label in dbrackets:
        if lo < t <= hi:
            db[label][0] += t
            db[label][1] += 1
            break
donor_size_out = [{"bracket": label, "amt": round(v[0], 2), "n": v[1]} for label, v in db.items()]

SKIP = {"NOT EMPLOYED", "RETIRED", "SELF", "SELF-EMPLOYED", "SELF EMPLOYED", "NONE",
        "N/A", "NA", "HOMEMAKER", "UNEMPLOYED", "STUDENT", ""}
emp = collections.defaultdict(lambda: [0.0, 0, set()])
for r in rows:
    e = (r.get("employer") or "").strip().upper()
    if e in SKIP:
        continue
    emp[e][0] += r["amt"]
    emp[e][1] += 1
    emp[e][2].add((r["last_norm"], r["first_norm"], (r.get("state") or "").upper()))
emp_out = sorted(
    [{"employer": k, "amt": round(v[0], 2), "n_gifts": v[1], "n_donors": len(v[2])}
     for k, v in emp.items()],
    key=lambda x: -x["amt"])[:30]

out = {
    "monthly": monthly_out,
    "gift_size": size_out,
    "states": states_out[:15],
    "mi_share_pct": round(states["MI"][0] / grand * 100, 1),
    "n_states": len(states),
    "donors": donor_out,
    "donor_size": donor_size_out,
    "top_employers": emp_out,
}
OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} gifts, {len(donors)} donors, "
      f"MI share {out['mi_share_pct']}%")
