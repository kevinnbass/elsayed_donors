"""Rank named-itemized dollars by occupation sector."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "analysis" / "roster_named_itemized.jsonl"

# First matching rule wins.
RULES: list[tuple[str, re.Pattern[str]]] = [
    ("Healthcare — physician / surgeon / specialist", re.compile(
        r"PHYSICIAN|DOCTOR|SURGEON|MD\b|D\.?O\.?\b|CARDIOLOG|ONCOLOG|PEDIATRICIAN|"
        r"PSYCHIATR|ANESTHESI|RADIOLOG|NEUROLOG|DERMATOLOG|HOSPITALIST|INTENSIVIST|"
        r"PATHOLOGIST|OB.?GYN|ORTHOPED|OPHTHALM|NEPHROLOG|RHEUMATOL|GASTROENTER|"
        r"PULMONOLOG|ENDOCRIN|UROLOG|NEONATOL|NEUROSURG", re.I)),
    ("Healthcare — other clinician (dentist, pharmacist, nurse, etc.)", re.compile(
        r"DENTIST|DDS|DMD|PHARMACIST|PHARMD|NURSE|RN\b|LPN|NP\b|CRNA|"
        r"NURSE PRACTITIONER|PHYSICIAN ASSISTANT|PA-C|PSYCHOLOGIST|THERAPIST|"
        r"CHIROPRACT|OPTOMETR|SOCIAL WORKER", re.I)),
    ("Healthcare — hospital / system / 'healthcare' staff", re.compile(
        r"HEALTHCARE|HEALTH CARE|MEDICAL|HOSPITAL|CLINICAL|PUBLIC HEALTH|"
        r"EPIDEMIOLOG|CMO\b|CHIEF MEDICAL", re.I)),
    ("Not employed / retired / student", re.compile(
        r"NOT EMPLOYED|UNEMPLOYED|RETIRED|NONE|N/?A\b|HOMEMAKER|STUDENT|"
        r"DISABLED|NOT EMPLOYED", re.I)),
    ("Law", re.compile(r"ATTORNEY|LAWYER|LEGAL|COUNSEL|JUDGE|LAW PROFESSOR|PARALEGAL", re.I)),
    ("Tech / engineering", re.compile(
        r"ENGINEER|SOFTWARE|PROGRAMMER|DEVELOPER|DATA SCIEN|PRODUCT MANAGER|"
        r"TECHNOLOG|IT\b|COMPUTER|SRE\b|DEVOPS", re.I)),
    ("Education / academic", re.compile(
        r"PROFESSOR|TEACHER|EDUCATOR|LECTURER|ACADEMIC|UNIVERSITY|FACULTY|"
        r"PRINCIPAL|SCHOOL", re.I)),
    ("Finance / investing", re.compile(
        r"FINANCE|INVEST|BANKER|ANALYST|ACCOUNTANT|CPA\b|HEDGE|PRIVATE EQUITY|"
        r"VENTURE|WEALTH|TRADER|CFO\b", re.I)),
    ("Business owner / executive / consultant (non-health)", re.compile(
        r"CEO|FOUNDER|OWNER|PRESIDENT|EXECUTIVE|CONSULTANT|ENTREPRENEUR|"
        r"MANAGING DIR|PARTNER|DIRECTOR|MANAGER|SELF EMPLOYED|SELF-EMPLOYED", re.I)),
    ("Government / politics / nonprofit", re.compile(
        r"GOVERNMENT|PUBLIC SERV|CIVIL SERV|ORGANIZER|ACTIVIST|NONPROFIT|"
        r"NON-PROFIT|POLICY|CAMPAIGN|UNION|ORGANIZER", re.I)),
    ("Media / arts / other professional", re.compile(
        r"WRITER|JOURNALIST|ARTIST|ACTOR|ACTRESS|DESIGNER|ARCHITECT|"
        r"MARKETING|SALES|REAL ESTATE|FARMER", re.I)),
]


def sector(occ: str, emp: str) -> str:
    blob = f"{occ} {emp}"
    for name, pat in RULES:
        if pat.search(occ or "") or (name.startswith("Healthcare") and pat.search(emp or "")):
            return name
    if not (occ or "").strip() or (occ or "").strip() in {"", "NULL", "NONE"}:
        return "Blank / unknown occupation"
    return "Other / unclassified"


def main() -> None:
    tot = 0.0
    n = 0
    buckets = defaultdict(lambda: {"n": 0, "amt": 0.0})
    occ_in = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
    with ROSTER.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            tot += r["amt"]
            n += 1
            s = sector(r.get("occupation") or "", r.get("employer") or "")
            buckets[s]["n"] += 1
            buckets[s]["amt"] += r["amt"]
            occ_in[s][(r.get("occupation") or "").strip() or "(blank)"][0] += 1
            occ_in[s][(r.get("occupation") or "").strip() or "(blank)"][1] += r["amt"]

    ranked = sorted(buckets.items(), key=lambda kv: -kv[1]["amt"])
    out = {
        "named_itemized_total": round(tot, 2),
        "n_gifts": n,
        "sectors": [],
    }
    print(f"Named itemized ${tot:,.2f}  n={n}\n")
    for i, (name, b) in enumerate(ranked, 1):
        pct = 100.0 * b["amt"] / tot
        rec = {
            "rank": i,
            "sector": name,
            "amt": round(b["amt"], 2),
            "pct": round(pct, 1),
            "n_gifts": b["n"],
            "top_occupations": [
                {"occ": o, "n": c, "amt": round(a, 2)}
                for o, (c, a) in sorted(occ_in[name].items(), key=lambda kv: -kv[1][1])[:6]
            ],
        }
        out["sectors"].append(rec)
        print(f"{i}. {name} — ${b['amt']:,.0f} — {pct:.1f}% — {b['n']:,} gifts")
        for o in rec["top_occupations"][:3]:
            print(f"      {o['occ']}: ${o['amt']:,.0f}")

    # healthcare rollup
    hc = [s for s in out["sectors"] if s["sector"].startswith("Healthcare")]
    hc_amt = sum(s["amt"] for s in hc)
    print(f"\nHEALTHCARE COMBINED — ${hc_amt:,.0f} — {100*hc_amt/tot:.1f}%")
    out["healthcare_combined"] = {
        "amt": round(hc_amt, 2),
        "pct": round(100.0 * hc_amt / tot, 1),
    }
    dest = ROOT / "analysis" / "sector_breakdown.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("WROTE", dest)


if __name__ == "__main__":
    main()
