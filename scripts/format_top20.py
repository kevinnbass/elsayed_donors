"""Rebuild the physician and health-employer lists on net donor totals.

Reads analysis/donors_net.jsonl (scripts/top_donors.py) and the NPPES name+state match
(analysis/nppes_donor_matches.jsonl). Writes analysis/top20_physicians_and_systems.json
and analysis/TOP20.txt. No states in the text (as before).

- Physicians: NPPES-confirmed (unique last+first+state NPI is 207/208, or every
  same-name NPI is) donors at the $7,000 maximum. 86 are tied there, so all are listed.
- Health employers: employer labels ranked by net dollars from donors in the three
  health-care sectors. A donor's net is split across their employer labels by gross share.
  Labels are compared upper-cased; variants (Henry Ford / Henry Ford Health) are not merged.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
CAP = 7000.0
SKIP = {"", "NOT EMPLOYED", "RETIRED", "SELF", "SELF-EMPLOYED", "SELF EMPLOYED", "NONE",
        "N/A", "NA", "HOMEMAKER", "UNEMPLOYED", "STUDENT", "INFORMATION REQUESTED"}

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sector_breakdown import HC_PHYS  # noqa: E402


def label(e: str) -> str:
    return re.sub(r"\s+", " ", (e or "").strip().upper()).strip(" .,")


def main() -> None:
    donors = [json.loads(line) for line in (ANALYSIS / "donors_net.jsonl").open(encoding="utf-8")]
    by_key = defaultdict(list)
    for r in donors:
        st = (r["state"] or "").upper()
        by_key[(r["last_norm"], r["first_norm"], st)].append(r)
        first_word = r["first_norm"].split(" ")[0] if r["first_norm"] else ""
        if first_word != r["first_norm"]:
            by_key[(r["last_norm"], first_word, st)].append(r)

    phys = []
    with (ANALYSIS / "nppes_donor_matches.jsonl").open(encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            if m["nppes_verdict"] != "confirmed_physician":
                continue
            matches = by_key.get((m["last_norm"], m["first_norm"], m["state"]), [])
            for r in matches:
                if r["net"] < CAP - 0.005:
                    continue
                phys.append({
                    "name": r["name"],
                    "state": r["state"],
                    "zip5": r["zip5"],
                    "net": r["net"],
                    "occupation": r["occupation"],
                    "fec_says_physician": r["sector"] == HC_PHYS,
                    "npi": m["npis"][0] if len(m["npis"]) == 1 else m["npis"],
                    "taxonomy": m["taxonomies"],
                    "donors_sharing_name_in_state": len(matches),
                })
    phys.sort(key=lambda r: (-r["net"], r["name"]))

    emp_amt: dict = defaultdict(float)
    emp_donors: dict = defaultdict(set)
    emp_spelling: dict = defaultdict(lambda: defaultdict(float))
    for r in donors:
        if not r["sector"].startswith("Healthcare"):
            continue
        gross = {e: a for e, a in r["employers_gross"].items() if label(e) not in SKIP and a > 0}
        tot = sum(gross.values())
        for e, a in gross.items():
            emp_amt[label(e)] += r["net"] * a / tot
            emp_donors[label(e)].add((r["last_norm"], r["first_norm"], r["zip5"]))
            emp_spelling[label(e)][e.strip()] += a
    employers = [
        {"employer": max(emp_spelling[k], key=emp_spelling[k].get), "label": k,
         "net": round(a, 2), "n_donors": len(emp_donors[k])}
        for k, a in sorted(emp_amt.items(), key=lambda kv: -kv[1])
    ][:20]
    henry_ford = sum(a for k, a in emp_amt.items() if k.startswith("HENRY FORD") and "COLLEGE" not in k)
    corewell = sum(a for k, a in emp_amt.items() if k.startswith("COREWELL"))

    out = {
        "basis": "net of refunds and reattributions (scripts/top_donors.py)",
        "n_nppes_confirmed_physicians_at_cap": len(phys),
        "nppes_confirmed_physicians_at_cap": phys,
        "top20_health_employers": employers,
        "henry_ford_labels_combined": round(henry_ford, 2),
        "corewell_labels_combined": round(corewell, 2),
    }
    (ANALYSIS / "top20_physicians_and_systems.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    both = [r for r in phys if r["fec_says_physician"]]
    name_only = [r for r in phys if not r["fec_says_physician"]]

    def row(r: dict) -> str:
        flag = " *" if r["donors_sharing_name_in_state"] > 1 else ""
        return f"{r['name']} — ${r['net']:,.0f} — {r['occupation'] or '—'}{flag}"

    lines = [
        "NPPES-confirmed physicians at the $7,000 maximum (net of refunds and reattributions)",
        f"{len(phys)} gave the maximum, so a top 20 would be an arbitrary cut; all are listed.",
        "NPPES-confirmed = last+first+state matches only physician NPIs. That is inference, not identity.",
        "\"*\" marks a name shared by another donor in the same state.",
        "",
        f"FEC occupation also says physician ({len(both)}):",
        "",
    ]
    lines += [row(r) for r in both]
    lines += [
        "",
        f"Name match only — FEC occupation is something else, may be a different person ({len(name_only)}):",
        "",
    ]
    lines += [row(r) for r in name_only]
    lines += [
        "",
        "Top 20 employers of health-care donors (net $ from physicians, other clinicians and",
        "health staff who listed that employer)",
        f"Label variants are not merged: Henry Ford labels combined ${henry_ford:,.0f}; "
        f"Corewell labels combined ${corewell:,.0f}.",
        "",
    ]
    lines += [f"{e['employer']} — ${e['net']:,.0f} — {e['n_donors']} donors" for e in employers]
    text = "\n".join(lines) + "\n"
    (ANALYSIS / "TOP20.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
