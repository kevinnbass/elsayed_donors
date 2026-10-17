"""Screen every campaign and super PAC donor against official U.S. terror-finance records.

Usage: python scripts/mb_record_screen.py <records.jsonl> <out_dir>
  <records.jsonl>  one row per person-appearance in an official record (convicted, charged, officer of a designated
                   charity, civil terrorism judgment, Holy Land Foundation Attachment A listing), each with a saved,
                   hashed source and a verbatim quote (built by the reference lane; see its SUMMARY.md).
  <out_dir>        the private claims folder: reads donors via analysis/donors_net.jsonl and <out_dir>/super_pac_receipts.jsonl;
                   writes <out_dir>/donor_record_screen.jsonl/.csv
Names are compared after the OFAC screen's transliteration folding (scripts/sdn_screen.py): a candidate needs the same
first name and the same final surname token. (The consonant-skeleton index is used only to find candidates quickly;
skeletons alone collide, e.g. KENAWY/KHAN.) A name match is a candidate, never a finding: the records mostly give a
name and a state, so identity is settled pair by pair from the records (identity review), not here. A control
checks the name stage: listed people entered as donors must all come back as candidates.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sdn", ROOT / "scripts" / "sdn_screen.py")
sdn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdn)
tokens, skel = sdn.tokens, sdn.skel

RECORDS, OUT = Path(sys.argv[1]), Path(sys.argv[2])
records = [json.loads(l) for l in open(RECORDS, encoding="utf-8") if l.strip()]


def name_parts(name: str) -> tuple[list[str], list[str]]:
    """(last-name tokens, first-name tokens) for 'Last, First' or 'First [Middle] Last'."""
    if "," in name:
        last, first = name.split(",", 1)
        return tokens(last), tokens(first)
    t = tokens(name)
    return (t[1:], t[:1]) if len(t) > 1 else ([], [])


index = defaultdict(set)
for i, r in enumerate(records):
    for nm in [r["person"], *(r.get("aliases") or [])]:
        lt, ft = name_parts(nm)
        for l_ in lt:
            if ft:
                index[(skel(l_), skel(ft[0]))].add(i)


def candidates(name: str) -> set[int]:
    lt, ft = name_parts(name)
    hits = set()
    for l_ in lt:
        if ft:
            hits |= index.get((skel(l_), skel(ft[0])), set())
    return hits


STATES = {"ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA", "COLORADO": "CO",
          "CONNECTICUT": "CT", "DELAWARE": "DE", "DISTRICT OF COLUMBIA": "DC", "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI",
          "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA",
          "MAINE": "ME", "MARYLAND": "MD", "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
          "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ",
          "NEW MEXICO": "NM", "NEW YORK": "NY", "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
          "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD",
          "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA",
          "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY"}


def state_code(s: str | None) -> str:
    s = (s or "").strip().upper()
    return STATES.get(s, s if len(s) == 2 else "")


def strict(a: str, b: str) -> bool:
    la, fa = name_parts(a)
    lb, fb = name_parts(b)
    return bool(la and lb and fa and fb and fa[0] == fb[0] and la[-1] == lb[-1])


donors = [{"name": d["name"], "city": d["city"], "state": d["state"], "committee": "Abdul for U.S. Senate", "net": d["net"],
           "occupation": d["occupation"], "employer": d["employer"]}
          for d in map(json.loads, open(ROOT / "analysis" / "donors_net.jsonl", encoding="utf-8"))]
pac = defaultdict(lambda: {"amount": 0.0})
for r in map(json.loads, open(OUT / "super_pac_receipts.jsonl", encoding="utf-8")):
    if r.get("entity_type") == "IND":
        k = (r["committee"], " ".join(r["contributor"].split()), r["city"], r["state"])
        pac[k]["amount"] += r["amount"] or 0
        pac[k].update(occupation=r["occupation"], employer=r["employer"])
donors += [{"name": k[1], "city": k[2], "state": k[3], "committee": k[0], "net": v["amount"],
            "occupation": v["occupation"], "employer": v["employer"]} for k, v in pac.items()]


def screen(ds: list[dict]) -> list[dict]:
    out = []
    for d in ds:
        for i in sorted(candidates(d["name"])):
            r = records[i]
            if not strict(d["name"], r["person"]):
                continue
            out.append({"donor": d["name"], "donor_city": d["city"], "donor_state": d["state"], "committee": d["committee"],
                        "amount": d["net"], "donor_occupation": d["occupation"], "donor_employer": d["employer"],
                        "record_person": r["person"], "record_category": r["category"], "record_case": r.get("case_or_action"),
                        "record_outcome": r.get("outcome"), "record_city": r.get("city"), "record_state": r.get("state"),
                        "record_birth_year": r.get("birth_year"), "record_source": r.get("source_url"),
                        "record_sha256": r.get("sha256"), "record_note": (r.get("note") or "")[:300],
                        "state_match": bool(state_code(r.get("state")) and state_code(r.get("state")) == (d["state"] or "").upper()),
                        "status": "name candidate: identity unreviewed (not a finding)"})
    return out


hits = screen(donors)
# identity review of the candidates (one verdict per donor x record pair), when it exists
REVIEW = RECORDS.parent / "identity_review.jsonl"
if REVIEW.exists():
    import hashlib
    verdicts = {json.loads(l)["pair_id"]: json.loads(l) for l in open(REVIEW, encoding="utf-8") if l.strip()}
    for h in hits:
        pid = hashlib.sha1(f"{h['donor']}|{h['donor_city']}|{h['donor_state']}|{h['record_person']}|{h['record_sha256']}".encode()).hexdigest()[:12]
        v = verdicts.get(pid)
        h["identity_verdict"] = v["verdict"] if v else "not reviewed"
        h["identity_reason"] = v.get("reason") if v else None
        h["status"] = {"same_person": "same person: finding", "different_person": "different person",
                       "unresolved": "unresolved name match: not a finding"}.get(h["identity_verdict"], h["status"])
# control on the name stage: every listed person, entered as a donor in "Last, First" form, must come back
ctl_people = [r for r in records if len(name_parts(r["person"])[0]) and "," not in r["person"]][:200]
ctl = screen([{"name": f"{r['person'].split()[-1]}, {r['person'].split()[0]}", "city": "", "state": "", "committee": "CONTROL",
               "net": 0, "occupation": "", "employer": ""} for r in ctl_people])
caught = {h["donor"] for h in ctl}
with (OUT / "donor_record_screen.jsonl").open("w", encoding="utf-8") as f:
    for h in hits:
        f.write(json.dumps(h, ensure_ascii=False) + "\n")
if hits:
    with (OUT / "donor_record_screen.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(hits[0]))
        w.writeheader()
        w.writerows(hits)
print(f"records {len(records)} | donors screened {len(donors)} (campaign {sum(d['committee'] == 'Abdul for U.S. Senate' for d in donors)}, "
      f"super PAC {sum(d['committee'] != 'Abdul for U.S. Senate' for d in donors)}) | name candidates {len(hits)} "
      f"({len({(h['donor'], h['donor_city']) for h in hits})} donors) | same state as the record {sum(1 for h in hits if h['state_match'])}"
      f"\nby record category: {dict(Counter(h['record_category'] for h in hits))}"
      f"\nidentity review: {dict(Counter(h.get('identity_verdict', 'not reviewed') for h in hits))}"
      f"\ncontrol (name stage): {len(caught)}/{len({(r['person'].split()[-1], r['person'].split()[0]) for r in ctl_people})} listed people entered as donors came back as candidates")
