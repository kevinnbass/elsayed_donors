"""Pin the stored cycle totals so a bad copy shows up immediately."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_named_itemized_matches_form3():
    summary = json.loads((ROOT / "analysis" / "roster_summary.json").read_text(encoding="utf-8"))
    assert summary["n"] == 31180
    assert summary["amt"] == 10265431.61
    assert summary["gap_vs_form3_itemized"] == 0.0


def test_nppes_floor_present():
    tight = json.loads(
        (ROOT / "analysis" / "healthcare_share_nppes_tight.json").read_text(encoding="utf-8")
    )
    assert tight["nppes_confirmed_physician_floor_pct"] == 20.08
    assert tight["named_itemized_total"] == 10265431.61


def test_top20_has_twenty():
    top = json.loads(
        (ROOT / "analysis" / "top20_physicians_and_systems.json").read_text(encoding="utf-8")
    )
    assert len(top["top20_nppes_confirmed_physicians"]) == 20
    assert len(top["top20_health_systems_by_dollars"]) == 20
