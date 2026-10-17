"""Match named itemized donors to NPPES physicians and compute the physician share of named dollars.

Usage (needs psycopg2 and the hhs_doge DB helper, i.e. the hhs_doge venv):
    ~/code/hhs_doge/.venv/bin/python scripts/nppes_share.py [roster.jsonl] [out_dir]
Defaults: analysis/roster_named_itemized.jsonl -> analysis/.

Same rules as scripts/recompute/elsayed_nppes_and_q1.py + elsayed_nppes_tighten.py, without
their lake-ingest side effects: donors are rolled up by last + first + state (gross $), joined to
lake.nppes_full individuals on the same normalized last name, first token and practice or
mailing state; taxonomy 207/208 = physician. Floor = unique NPPES match that is a physician, or
every same-name+state NPI is one; mixed homonyms are not in the floor. Read-only on the DB
(one temp table).

Writes nppes_donor_matches.jsonl and healthcare_share_nppes_tight.json into out_dir.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HHS_DOGE = Path.home() / "code" / "hhs_doge"
sys.path.insert(0, str(HHS_DOGE))
from src.db import get_connection  # noqa: E402

PHYS_OCC = re.compile(
    r"PHYSICIAN|DOCTOR|SURGEON|MD\b|CARDIOLOG|ONCOLOG|PEDIATRICIAN|"
    r"PSYCHIATRIST|ANESTHESI|RADIOLOGIST|NEUROLOGIST|DERMATOLOG|"
    r"HOSPITALIST|INTENSIVIST|PATHOLOGIST|OB.?GYN|ORTHOPED",
    re.I,
)
CLIN_OCC = re.compile(
    r"\b(PHYSICIAN|DOCTOR|SURGEON|MD\b|DENTIST|PHARMACIST|NURSE|RN\b|"
    r"NURSE PRACTITIONER|PHYSICIAN ASSISTANT|PSYCHOLOGIST|THERAPIST|"
    r"CHIROPRACT|OPTOMETR|SOCIAL WORKER|CARDIOLOG|ONCOLOG|RADIOLOG|"
    r"DERMATOLOG|HOSPITALIST|NEPHROLOG|OPHTHALM)",
    re.I,
)
PHYS_TAX = re.compile(r"^(207|208)")
CONFIRMED_V = {"confirmed_physician", "all_hits_physician_ambiguous"}
MIXED_V = {"mixed_hits_some_physician"}


def nppes_match(keys: list[tuple[str, str, str]]) -> dict:
    con = get_connection()
    con.execute("SET statement_timeout = '300s'")
    con.execute("SET lock_timeout = '20s'")
    con.execute("CREATE TEMP TABLE tmp_elsayed_nppes_keys (last_norm text, first_norm text, state text)")
    con.executemany("INSERT INTO tmp_elsayed_nppes_keys VALUES (%s,%s,%s)", sorted(set(keys)))
    rows = con.execute(
        """
        SELECT k.last_norm, k.first_norm, k.state, n.npi, n.taxonomy_code_1
        FROM tmp_elsayed_nppes_keys k
        JOIN lake.nppes_full n
          ON n.entity_type = 1
         AND upper(regexp_replace(n.provider_last_name, '[^A-Za-z0-9]+', ' ', 'g')) = k.last_norm
         AND split_part(upper(regexp_replace(n.provider_first_name, '[^A-Za-z0-9]+', ' ', 'g')), ' ', 1)
             = k.first_norm
         AND (n.provider_practice_state = k.state OR n.provider_mailing_state = k.state)
        """
    ).fetchall()
    con.close()
    by = defaultdict(list)
    for r in rows:
        by[(r[0], r[1], r[2])].append({"npi": r[3], "taxonomy": r[4] or ""})
    return by


def adjudicate(hits: list[dict]) -> dict:
    if not hits:
        return {"verdict": "unmatched", "n_npi": 0, "n_physician_npi": 0, "taxonomies": [], "npis": []}
    phys = [h for h in hits if PHYS_TAX.match(h["taxonomy"].strip())]
    unique = len(hits) == 1
    if unique:
        v = "confirmed_physician" if phys else "confirmed_nonphysician"
    elif phys and len(phys) == len(hits):
        v = "all_hits_physician_ambiguous"
    elif phys:
        v = "mixed_hits_some_physician"
    else:
        v = "matched_nonphysician_ambiguous"
    return {"verdict": v, "n_npi": len(hits), "n_physician_npi": len(phys),
            "taxonomies": sorted({h["taxonomy"] for h in hits if h["taxonomy"]})[:8],
            "npis": [h["npi"] for h in hits[:8]]}


def main() -> None:
    roster_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "analysis" / "roster_named_itemized.jsonl"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "analysis"
    roster = [json.loads(line) for line in roster_path.open(encoding="utf-8")]
    donor = defaultdict(lambda: {"amt": 0.0, "n": 0, "name": "", "occs": set(), "emps": set(),
                                 "phys": False, "clin": False})
    for r in roster:
        k = (r["last_norm"], r["first_norm"], r["state"])
        d = donor[k]
        d["amt"] += r["amt"]
        d["n"] += 1
        d["name"] = r["name"]
        d["occs"].add(r["occupation"])
        d["emps"].add(r["employer"])
        d["phys"] = d["phys"] or bool(PHYS_OCC.search(r["occupation"] or ""))
        d["clin"] = d["clin"] or bool(CLIN_OCC.search(r["occupation"] or ""))
    hits = nppes_match([k for k in donor if all(k)])

    tot = sum(d["amt"] for d in donor.values())
    tight = defaultdict(lambda: {"n_donors": 0, "n_gifts": 0, "amt": 0.0})
    with (out_dir / "nppes_donor_matches.jsonl").open("w", encoding="utf-8") as f:
        for k, d in sorted(donor.items(), key=lambda kv: -kv[1]["amt"]):
            adj = adjudicate(hits.get(k, []))
            v, fec_p = adj["verdict"], d["phys"]
            if v in CONFIRMED_V:
                lab = "confirmed_both" if fec_p else "confirmed_nppes_fec_silent"
            elif v in MIXED_V:
                lab = "mixed_homonym_not_in_floor"
            elif fec_p and v == "confirmed_nonphysician":
                lab = "dropped_fec_physician_unique_nonmd"
            elif fec_p and v == "unmatched":
                lab = "fec_physician_unmatched"
            elif fec_p:
                lab = "fec_physician_other"
            else:
                lab = "not_physician"
            b = tight[lab]
            b["n_donors"] += 1
            b["n_gifts"] += d["n"]
            b["amt"] += d["amt"]
            f.write(json.dumps({
                "name": d["name"], "state": k[2], "last_norm": k[0], "first_norm": k[1],
                "n_gifts": d["n"], "amt": round(d["amt"], 2),
                "fec_physician_occ": fec_p, "fec_clinician_occ": d["clin"],
                "occupations": sorted(d["occs"])[:8], "employers": sorted(d["emps"])[:8],
                "nppes_verdict": v, "n_npi": adj["n_npi"], "n_physician_npi": adj["n_physician_npi"],
                "taxonomies": adj["taxonomies"], "npis": adj["npis"], "tight_label": lab,
            }) + "\n")

    floor = tight["confirmed_both"]["amt"] + tight["confirmed_nppes_fec_silent"]["amt"]
    upper = floor + sum(tight[k]["amt"] for k in
                        ("fec_physician_unmatched", "fec_physician_other", "mixed_homonym_not_in_floor"))
    out = {
        "named_itemized_total": round(tot, 2),
        "n_donors": len(donor),
        "nppes_confirmed_physician_floor_dollars": round(floor, 2),
        "nppes_confirmed_physician_floor_pct": round(100.0 * floor / tot, 2),
        "upper_bound_dollars": round(upper, 2),
        "upper_bound_pct": round(100.0 * upper / tot, 2),
        "rule": ("Floor = unique NPPES individual with taxonomy 207/208, or every "
                 "same-name+state NPI is 207/208. Mixed homonyms are NOT in the floor."),
        "buckets": {k: {"n_donors": v["n_donors"], "n_gifts": v["n_gifts"], "amt": round(v["amt"], 2),
                        "pct": round(100.0 * v["amt"] / tot, 2)}
                    for k, v in sorted(tight.items(), key=lambda kv: -kv[1]["amt"])},
    }
    (out_dir / "healthcare_share_nppes_tight.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rule"}, indent=1))


if __name__ == "__main__":
    main()
