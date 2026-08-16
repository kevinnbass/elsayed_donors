"""Rewrite analysis/TOP20.txt: one people list, one employer list. No states."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
top = json.loads((ROOT / "analysis" / "top20_physicians_and_systems.json").read_text(encoding="utf-8"))


def pick_occ(occs: list[str] | None) -> str:
    junk = {"", "gee", "none", "n/a", "na"}
    cleaned = [o.strip() for o in (occs or []) if o and o.strip().lower() not in junk]
    if not cleaned:
        return "—"
    # prefer a clinical title if several
    for o in cleaned:
        if o.lower() not in {"not employed", "self employed", "self-employed"}:
            return o
    return cleaned[0]


lines = [
    "Top 20 physician donors (NPPES-confirmed MD/DO NPI, named itemized $)",
    "Issa, Said is a shaky name match: FEC occupation is dentist.",
    "",
]
for r in top["top20_nppes_confirmed_physicians"]:
    lines.append(f"{r['name']} — ${r['amt']:,.0f} — {pick_occ(r.get('occupations'))}")

lines += [
    "",
    "Top 20 health-system employers (dollars from anyone who listed that employer)",
    "Henry Ford is split across three labels (~$81k combined). Corewell + Corewell Health ~$49k.",
    "",
]
FIX = {
    "UNIVERSITY OF MICHIGAN": "University of Michigan",
    "HENRY FORD HEALTH": "Henry Ford Health",
    "COREWELL HEALTH": "Corewell Health",
    "WAYNE STATE UNIVERSITY": "Wayne State University",
    "PROMEDICA": "ProMedica",
    "TPMG": "TPMG",
    "PFIZER": "Pfizer",
    "MEMORIAL HEALTHCARE": "Memorial Healthcare",
    "MCLAREN": "McLaren",
    "KAISER PERMANENTE": "Kaiser Permanente",
    "HENRY FORD": "Henry Ford",
    "SEBMF": "SEBMF",
    "ASCENSION": "Ascension",
    "SUTTER WEST BAY MEDICAL GROUP": "Sutter West Bay Medical Group",
    "MERCY HEALTH": "Mercy Health",
    "HENRY FORD HOSPITAL": "Henry Ford Hospital",
    "HOSPITAL": "Hospital (generic label)",
    "TRINITY HEALTH": "Trinity Health",
    "UW HEALTH": "UW Health",
    "COREWELL": "Corewell",
}
for r in top["top20_health_systems_by_dollars"]:
    emp = FIX.get(r["employer"], r["employer"].title())
    lines.append(f"{emp} — ${r['amt']:,.0f}")

text = "\n".join(lines) + "\n"
(ROOT / "analysis" / "TOP20.txt").write_text(text, encoding="utf-8")
print(text)
