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
    print("=== Top 20 physician donors ===")
    for r in top["top20_nppes_confirmed_physicians"]:
        occs = [o for o in (r.get("occupations") or []) if o and o.strip().lower() not in {"gee", "none"}]
        occ = occs[0] if occs else "—"
        print(f"{r['name']} — ${r['amt']:,.0f} — {occ}")
    print()
    print("=== Top 20 health-system employers ===")
    for r in top["top20_health_systems_by_dollars"]:
        print(f"{r['employer'].title()} — ${r['amt']:,.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
