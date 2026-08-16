"""Print El-Sayed named-itemized shares and top-20 lists from local analysis files."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"


def main() -> int:
    summary = json.loads((ANALYSIS / "roster_summary.json").read_text(encoding="utf-8"))
    tight = json.loads((ANALYSIS / "healthcare_share_nppes_tight.json").read_text(encoding="utf-8"))
    top = json.loads((ANALYSIS / "top20_physicians_and_systems.json").read_text(encoding="utf-8"))

    print("Named itemized:", f"${summary['amt']:,.2f}", f"({summary['n']} gifts)")
    print("Form 3 itemized gap:", summary.get("gap_vs_form3_itemized"))
    print(
        "NPPES-confirmed MD floor:",
        f"${tight['nppes_confirmed_physician_floor_dollars']:,.2f}",
        f"({tight['nppes_confirmed_physician_floor_pct']}%)",
    )
    print(
        "NPPES MD upper bound:",
        f"${tight['upper_bound_dollars']:,.2f}",
        f"({tight['upper_bound_pct']}%)",
    )
    print()
    print("=== Top 20 NPPES-confirmed physicians ===")
    for r in top["top20_nppes_confirmed_physicians"]:
        occ = (r.get("occupations") or [""])[0]
        emp = (r.get("employers") or [""])[0]
        print(f"{r['name']} — {r['state']} — ${r['amt']:,.0f} — {occ} — {emp}")
    print()
    print("=== Top 20 health-system employers ===")
    for r in top["top20_health_systems_by_dollars"]:
        print(f"{r['employer']} — ${r['amt']:,.0f} — {r['n_gifts']} gifts — {r['n_names']} names")
    print()
    print("=== Top 20 people who listed a system ===")
    for r in top["top20_donors_employed_at_a_system"]:
        occ = ", ".join(r.get("occupations") or [])
        emp = ", ".join(r.get("employers") or [])
        print(f"{r['name']} — {r['state']} — ${r['amt']:,.0f} — {occ} — {emp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
