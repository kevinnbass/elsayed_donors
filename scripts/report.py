"""Print El-Sayed named-itemized shares and the physician / health-employer lists from local files."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"


def main() -> int:
    summary = json.loads((ANALYSIS / "roster_summary.json").read_text(encoding="utf-8"))
    tight = json.loads((ANALYSIS / "healthcare_share_nppes_tight.json").read_text(encoding="utf-8"))
    top = json.loads((ANALYSIS / "top20_physicians_and_systems.json").read_text(encoding="utf-8"))
    donors = json.loads((ANALYSIS / "top_donors.json").read_text(encoding="utf-8"))

    print("Named itemized:", f"${summary['amt']:,.2f}", f"({summary['n']} gifts)")
    print("Form 3 itemized gap:", summary.get("gap_vs_form3_itemized"))
    print("Individual net of refunds and reattributions:", f"${donors['individual_net_total']:,.2f}",
          f"({donors['n_individual_donors']:,} donors, {donors['n_at_cap']} at the $7,000 maximum)")
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
    print(f"=== NPPES-confirmed physicians at the $7,000 maximum ({top['n_nppes_confirmed_physicians_at_cap']}) ===")
    for r in top["nppes_confirmed_physicians_at_cap"]:
        print(f"{r['name']} — ${r['net']:,.0f} — {r['occupation'] or '—'}")
    print()
    print("=== Top 20 employers of health-care donors (net) ===")
    for r in top["top20_health_employers"]:
        print(f"{r['employer']} — ${r['net']:,.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
