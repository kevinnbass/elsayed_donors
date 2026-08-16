"""Unit tests for the Class-A FEC 2026 El-Sayed donor-base refresh drain.

Drives the shipped helpers in scripts/drain/drain_fec_2026_bulk_refresh.py
(date parse, itemized-individual classifier, authorized-cmte gate, header
contract, and the never-blacklist target list). Does not download.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRAIN = ROOT / "scripts" / "drain" / "drain_fec_2026_bulk_refresh.py"


def _load():
    spec = importlib.util.spec_from_file_location("drain_fec_2026_bulk_refresh", DRAIN)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def drain():
    return _load()


def test_parse_fec_mmddyyyy_iso(drain):
    assert drain.parse_fec_mmddyyyy("03102025") == "2025-03-10"
    assert drain.parse_fec_mmddyyyy("06302026") == "2026-06-30"
    assert drain.parse_fec_mmddyyyy("12312025") == "2025-12-31"
    assert drain.parse_fec_mmddyyyy("") is None
    assert drain.parse_fec_mmddyyyy("2025-03-10") is None
    assert drain.parse_fec_mmddyyyy("331226") is None


def test_itemized_individual_excludes_memo_and_refunds(drain):
    assert drain.is_itemized_individual("15", "") is True
    assert drain.is_itemized_individual("15E", "") is True
    assert drain.is_itemized_individual("15E", None) is True
    assert drain.is_itemized_individual("15", "X") is False
    assert drain.is_itemized_individual("22Y", "") is False
    assert drain.is_itemized_individual("15C", "") is False
    assert drain.is_itemized_individual("24K", "") is False


def test_authorized_donor_base_is_only_the_pcc(drain):
    assert drain.is_authorized_donor_base_cmte("C00902668") is True
    assert drain.is_authorized_donor_base_cmte(" C00902668 ") is True
    assert drain.is_authorized_donor_base_cmte("C00919373") is False
    assert drain.is_authorized_donor_base_cmte("C00799031") is False
    assert drain.is_authorized_donor_base_cmte("") is False


def test_itcont_header_matches_fec_bulk_mapping(drain):
    mappings = json.loads((ROOT / "config" / "header_mappings.json").read_text(encoding="utf-8"))
    official = mappings["fec_bulk"]["header_files"]["itcont.txt"]["columns"]
    assert drain.ITCONT_COLS == official
    assert "name" in drain.ITCONT_COLS
    assert "contributor_name" not in drain.ITCONT_COLS


def test_drain_targets_per_cycle_tables_never_blacklisted_megatables():
    src = DRAIN.read_text(encoding="utf-8")
    assert "fec_individual_contributions_2026" in src
    assert "fec_pac_to_candidate_2026" in src
    assert "https://www.fec.gov/files/bulk-downloads/2026/indiv26.zip" in src
    assert 'target_table="itcont"' not in src
    assert "target_table='itcont'" not in src
    assert 'target_table="drain_political_intel"' not in src
    assert 'target_table="queue_downloads_www_fec_gov"' not in src
    assert 'target_table="by_date_itcont_2026' not in src
    assert "Do not ingest into lake.itcont" in src


def test_queue_uses_strict_helper_and_class_a_host():
    src = DRAIN.read_text(encoding="utf-8")
    assert "queue_for_ingest_strict" in src
    assert "www.fec.gov/files/bulk-downloads/2026/" in src
    assert "playwright" not in src.lower()
    assert "2captcha" not in src.lower()
    assert "indiv26.zip" in src
