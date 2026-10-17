"""Screen every donor against OFAC's SDN list (individuals and their aliases).

Usage: python -I scripts/sdn_screen.py <dir with sdn.csv, alt.csv, add.csv> <candidates_out.json>

Two passes:
1. Name candidates. A donor is a candidate when their surname and first given name match an
   SDN individual's (primary name or alias) after transliteration folding (MOHAMMED/MUHAMMAD,
   ABDEL/ABDUL, AL-/EL- dropped, doubled letters and vowels collapsed). Deliberately loose.
2. Corroboration. A candidate counts as a match only if something beyond the name agrees:
   an SDN address in the United States in the donor's state (and city, when given).
   SDN listings without a U.S. address cannot be tied to a U.S. donor by name alone.

Control: synthetic donors built from real SDN individuals (one with a U.S. address placed at
that address) must come back as candidates / matches, or the screen could not see a hit.

Writes analysis/sdn_screen.json (counts, list vintage, control result, corroborated matches only).
Name-only candidates go to <candidates_out.json>, outside the repo: a shared name is not a
connection and is not published.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DONORS = ROOT / "analysis" / "donors_net.jsonl"
OUT = ROOT / "analysis" / "sdn_screen.json"

FOLD = [
    (r"\b(MOHAMM?[AE]D|MUHAMM?[AE]D|MOHAMM?[AE]DE?|MEHMET|MEHMED)\b", "MUHAMMAD"),
    (r"\b(AHMED|AHMET)\b", "AHMAD"),
    (r"\bABD[EU]?L?\b", "ABD"),
    (r"\b(ABDEL|ABDUL|ABDAL|ABDOUL)(?=[A-Z])", "ABD"),
    (r"\b(HUSS?[AE]IN|HUSS?AYN|HOSS?[AE]IN)\b", "HUSAYN"),
    (r"\b(YOUS?SEF|YUSUF|YOUSUF|YOUSIF|YUSEF)\b", "YUSUF"),
    (r"\bOMAR\b", "UMAR"),
    (r"\bKHALED\b", "KHALID"),
    (r"\bMAHMOUD\b", "MAHMUD"),
    (r"\bMOSTAFA\b", "MUSTAFA"),
    (r"\bEBRAHIM\b", "IBRAHIM"),
]
DROP = {"AL", "EL", "BIN", "BEN", "IBN", "ABU", "ABOU", "BINT", "DE", "LA", "MR", "MRS", "DR", "JR", "SR"}
MB_ORGS: list[dict] = []  # Muslim Brotherhood branches on the SDN list, filled by load_sdn


def tokens(s: str) -> list[str]:
    s = (s or "").upper().replace("'", "").replace(".", "")
    s = re.sub(r"\b(AL|EL)-", "", s)
    s = re.sub(r"[^A-Z ]+", " ", s)
    for pat, rep in FOLD:
        s = re.sub(pat, rep, s)
    return [t for t in s.split() if t and t not in DROP]


def skel(t: str) -> str:
    """Consonant skeleton: first letter kept, vowels/Y/W/H dropped after it, repeats collapsed."""
    t = t.replace("OU", "U").replace("EE", "I").replace("PH", "F").replace("Q", "K").replace("Z", "S")
    out = t[0]
    for c in t[1:]:
        if c in "AEIOUYWH":
            continue
        if out[-1] != c:
            out += c
    return out


def split_sdn_name(name: str) -> tuple[list[str], list[str]]:
    if "," in name:
        last, first = name.split(",", 1)
        return tokens(last), tokens(first)
    toks = tokens(name)
    return toks[-1:], toks[:-1]


def load_sdn(d: Path) -> tuple[dict, dict]:
    def rows(name: str):
        with (d / name).open(encoding="latin-1", newline="") as f:
            for r in csv.reader(f):
                if r and r[0].strip().isdigit():
                    yield [x.strip() for x in r]

    people = {}
    for r in rows("sdn.csv"):
        if "BROTHERHOOD" in r[1].upper():
            MB_ORGS.append({"ent_num": r[0], "name": r[1], "program": r[3]})
        if r[2] == "individual":
            people[r[0]] = {"ent_num": r[0], "name": r[1], "program": r[3], "remarks": r[11],
                            "names": [r[1]], "addresses": []}
    for r in rows("alt.csv"):
        if r[0] in people and r[3] and r[3] != "-0-":
            people[r[0]]["names"].append(r[3])
    for r in rows("add.csv"):
        if r[0] in people:
            people[r[0]]["addresses"].append({"street": r[2], "city_state_zip": r[3], "country": r[4]})

    index = defaultdict(set)  # (surname skeleton, first-given skeleton) -> ent_nums
    for e, p in people.items():
        for n in p["names"]:
            last, first = split_sdn_name(n)
            if not last or not first:
                continue
            for lt in last:
                index[(skel(lt), skel(first[0]))].add(e)
    return people, index


def candidates_for(last: str, first: str, index: dict) -> set[str]:
    lt, ft = tokens(last), tokens(first)
    if not lt or not ft:
        return set()
    hits = set()
    for t in lt:
        hits |= index.get((skel(t), skel(ft[0])), set())
    return hits


US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC",
    "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "PR", "GU", "VI"}


def corroborate(donor: dict, p: dict) -> list[str]:
    """Reasons beyond the name that tie this SDN listing to this donor (empty = name only)."""
    reasons = []
    for a in p["addresses"]:
        if "UNITED STATES" not in (a["country"] or "").upper():
            continue
        csz = (a["city_state_zip"] or "").upper()
        state_ok = bool(re.search(r"\b" + re.escape(donor["state"]) + r"\b", csz)) if donor["state"] else False
        city_ok = bool(donor["city"]) and donor["city"].upper() in csz
        if state_ok and (city_ok or not re.sub(r"[^A-Z]", "", csz.replace(donor["state"], ""))):
            reasons.append(f"SDN U.S. address {a['city_state_zip']} matches donor {donor['city']}, {donor['state']}")
    return reasons


def screen(donors: list[dict], people: dict, index: dict) -> list[dict]:
    out = []
    for d in donors:
        last, _, first = (d["name"] or "").partition(",")
        for e in sorted(candidates_for(last, first, index)):
            p = people[e]
            out.append({
                "donor": d["name"], "city": d["city"], "state": d["state"], "zip5": d["zip5"],
                "occupation": d["occupation"], "employer": d["employer"], "net": d["net"],
                "sdn_ent_num": e, "sdn_name": p["name"], "sdn_program": p["program"],
                "sdn_countries": sorted({a["country"] for a in p["addresses"] if a["country"] and a["country"] != "-0-"}),
                "sdn_remarks": p["remarks"][:400],
                "corroboration": corroborate(d, p),
            })
    return out


def control(people: dict, index: dict) -> dict:
    rng = random.Random(20261016)
    pool = [p for p in people.values() if "," in p["name"] and split_sdn_name(p["name"])[1]]
    picks = rng.sample(pool, 200)
    synth = []
    for p in picks:
        last, first = p["name"].split(",", 1)
        synth.append({"name": f"{last.title()}, {first.strip().split()[0].title()}", "city": "", "state": "",
                      "zip5": "", "occupation": "", "employer": "", "net": 0.0, "_ent": p["ent_num"]})
    found = sum(1 for s in synth if s["_ent"] in candidates_for(*s["name"].split(",", 1), index))
    # a listing with a U.S. address, placed at that address, must corroborate
    us = None
    for p in people.values():
        for a in p["addresses"]:
            m = re.match(r"^(.*?),\s*([A-Z]{2})\b", (a["city_state_zip"] or "").upper())
            if "UNITED STATES" in (a["country"] or "").upper() and m and m.group(2) in US_STATES and "," in p["name"]:
                us = (p, m.group(1).strip().title(), m.group(2))
                break
        if us:
            break
    us_ok = None
    if us:
        p, city, st = us
        last, first = p["name"].split(",", 1)
        d = {"name": f"{last.title()}, {first.strip().split()[0].title()}", "city": city, "state": st,
             "zip5": "", "occupation": "", "employer": "", "net": 0.0}
        hits = screen([d], people, index)
        us_ok = any(h["sdn_ent_num"] == p["ent_num"] and h["corroboration"] for h in hits)
    return {"synthetic_from_sdn": len(synth), "found_as_candidates": found,
            "us_address_listing_corroborated": us_ok,
            "us_address_listing_used": us[0]["name"] if us else None}


def main() -> None:
    sdn_dir, cand_out = Path(sys.argv[1]), Path(sys.argv[2])
    people, index = load_sdn(sdn_dir)
    donors = [json.loads(line) for line in DONORS.open(encoding="utf-8")]
    hits = screen(donors, people, index)
    matches = [h for h in hits if h["corroboration"]]
    ctl = control(people, index)
    n_cand_donors = len({(h["donor"], h["zip5"]) for h in hits})

    # individuals OFAC links to a Muslim Brotherhood branch; control: each, entered as a
    # donor under its own and a variant spelling, must come back as a candidate
    mb_people = {e: p for e, p in people.items()
                 if re.search(r"Linked To:[^;]*BROTHERHOOD", p["remarks"], re.I)}
    mb_control = {}
    for e, p in mb_people.items():
        last, first = p["name"].split(",", 1)
        variant_first = re.sub(r"MUHAMMAD|MAHMOUD", lambda m: {"MUHAMMAD": "MOHAMMED", "MAHMOUD": "MAHMUD"}[m.group(0)],
                               first.strip().split()[0].upper())
        mb_control[p["name"]] = all(e in candidates_for(last, f, index) for f in (first, variant_first))
    muslim_brotherhood = {
        "branches_on_sdn": MB_ORGS,
        "individuals_linked_to_a_branch": [
            {"ent_num": e, "name": p["name"], "program": p["program"],
             "linked_to": re.search(r"Linked To:[^;.]*", p["remarks"]).group(0)} for e, p in mb_people.items()],
        "donor_name_candidates": sum(1 for h in hits if h["sdn_ent_num"] in mb_people),
        "control_caught": mb_control,
    }
    at_cap = {(d["name"], d["zip5"]) for d in donors if d["net"] >= 6999.995}
    out = {
        "sdn_files_sha256": {f: hashlib.sha256((sdn_dir / f).read_bytes()).hexdigest()
                             for f in ("sdn.csv", "alt.csv", "add.csv")},
        "n_sdn_individuals": len(people),
        "n_donors_screened": len(donors),
        "n_donors_with_name_candidates": n_cand_donors,
        "n_donors_at_max": len(at_cap),
        "n_candidates_among_donors_at_max": len({(h["donor"], h["zip5"]) for h in hits} & at_cap),
        "n_corroborated_matches": len(matches),
        "corroborated_matches": matches,
        "control": ctl,
        "muslim_brotherhood": muslim_brotherhood,
        "manual_review": (
            "Data through Sep 30, 2026: the 47 candidate pairs whose SDN record mentions the U.S. "
            "(12 listings) were read by hand; none is the donor: MURAD, Abdul Hakim (alias AHMED, Saeed; "
            "incarcerated in the U.S.) x24, HIJAZI, Riad (aliases Abu-Ahmad; address Jordan) x5, AHMADY, "
            "Ali Fotowat (address Tehran) x5, AHMAD, Firas Nazem (address Johannesburg; donor first name "
            "Farisa) x1, and 8 DPRK listings whose only U.S. text is sanctions boilerplate x12."),
        "rule": __doc__.strip().split("\n\n")[1],
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    cand_out.write_text(json.dumps(hits, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("corroborated_matches", "rule")}, indent=1))


if __name__ == "__main__":
    main()
