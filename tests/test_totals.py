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


def test_physician_and_employer_lists():
    top = json.loads(
        (ROOT / "analysis" / "top20_physicians_and_systems.json").read_text(encoding="utf-8")
    )
    phys = top["nppes_confirmed_physicians_at_cap"]
    assert top["n_nppes_confirmed_physicians_at_cap"] == len(phys) == 86
    assert all(r["net"] >= 7000 for r in phys)
    assert len(top["top20_health_employers"]) == 20


def test_top_donors_net_reconciles():
    t = json.loads((ROOT / "analysis" / "top_donors.json").read_text(encoding="utf-8"))
    # roster IND gross 10,246,881.61 + reattribution memos 10,500.00 - SB20A refunds 61,682.15
    assert t["individual_net_total"] == 10195699.46
    assert t["n_at_cap"] == 446
    assert t["unmatched_refunds"] == []
    assert all(r["committee_check"] != "differs" for r in t["over_cap"])


def test_top100_is_a_reproducible_draw_from_the_max():
    t = json.loads((ROOT / "analysis" / "top_donors.json").read_text(encoding="utf-8"))
    draw = t["top100_random_from_cap"]
    assert draw["seed"] == "elsayed-top100-2026-10-16"
    assert draw["pool"] == 446
    assert len(draw["donors"]) == 100
    assert all(r["net"] >= 7000 for r in draw["donors"])


def test_sector_rules():
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from sector_breakdown import sector

    cases = {
        ("Engineer", "AMD"): "Tech / engineering",
        ("Professor", "Eastern Michigan University"): "Education / academic",
        ("Graduate Student", "University of Toledo"): "Not employed / retired / student",
        ("Nonprofit", "Sierra Club"): "Government / politics / nonprofit",
        ("Contractor", "Self Employed"): "Other / unclassified",
        ("Hospitality", "Hadidi Hospitality"): "Other / unclassified",
        ("Physician Assistant", "Self Employed"): "Healthcare — other clinician (dentist, pharmacist, nurse, etc.)",
        ("Physcian", "Self Employed"): "Healthcare — physician / surgeon / specialist",
        ("Sutter", "Physician"): "Healthcare — physician / surgeon / specialist",
        ("Retired", "Henry Ford Health"): "Not employed / retired / student",
        ("Attorney", "Henry Ford Health"): "Healthcare — hospital / system / 'healthcare' staff",
        ("Information Requested", "Information Requested"): "Blank / unknown occupation",
    }
    for (occ, emp), want in cases.items():
        assert sector(occ, emp) == want, (occ, emp)
    sb = json.loads((ROOT / "analysis" / "sector_breakdown.json").read_text(encoding="utf-8"))
    assert sb["named_itemized_total"] == 10265431.61
    assert sb["healthcare_combined"]["pct"] == 28.8
