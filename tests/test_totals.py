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


def test_name_token_shares():
    mus = json.loads((ROOT / "analysis" / "muslim_name_share.json").read_text(encoding="utf-8"))
    nw = json.loads((ROOT / "analysis" / "nonwhite_name_share.json").read_text(encoding="utf-8"))
    assert mus["named_itemized_total"] == 10265431.61
    assert mus["label"] == "arab_or_muslim"
    assert mus["any_name_token"]["pct"] == 64.7
    assert nw["nonwhite_coded"]["pct"] == 66.9
    assert nw["nonwhite_coded"]["pct"] > mus["any_name_token"]["pct"]


def test_top20_has_twenty():
    top = json.loads(
        (ROOT / "analysis" / "top20_physicians_and_systems.json").read_text(encoding="utf-8")
    )
    assert len(top["top20_nppes_confirmed_physicians"]) == 20
    assert len(top["top20_health_systems_by_dollars"]) == 20


def test_top_donors_net_reconciles():
    t = json.loads((ROOT / "analysis" / "top_donors.json").read_text(encoding="utf-8"))
    # roster IND gross 10,246,881.61 + reattribution memos 10,500.00 - SB20A refunds 61,682.15
    assert t["individual_net_total"] == 10195699.46
    assert t["n_at_cap"] == 446
    assert t["unmatched_refunds"] == []
    assert all(r["committee_check"] != "differs" for r in t["over_cap"])
