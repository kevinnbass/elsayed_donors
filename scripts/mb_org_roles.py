"""Donors' documented roles in the organizations the coverage names (self-reported employer, and organization rosters).

Usage: python scripts/mb_org_roles.py <out_dir> [<rosters.jsonl> ...]
  Step 1, always: every itemized gift (campaign roster, joint-committee shares, super PAC receipts) whose self-reported
    employer or occupation names an organization in ORGS. Self-reported on the donor's own filing, so identity is direct.
  Step 2, when roster files are given: names listed as officers, directors, staff or founders of those organizations in
    primary records (Form 990s, the organizations' own pages, state registries), one JSON row per listing:
    {"org", "person", "role", "years", "city", "state", "source_url", "sha256", "quote"}. Donors whose name matches are
    written as candidates; a match is confirmed only by a second attribute (city/state, employer, occupation, or a
    record tying the two), never on the name alone.
Writes <out_dir>/donor_org_roles.jsonl/.csv. Roles are stated plainly (no characterization of the organization).
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1])
ROSTERS = [Path(p) for p in sys.argv[2:]]

# organizations the coverage names; patterns for how filers write them in the employer/occupation fields
ORGS = {
    "CAIR (incl. chapters, CAIR Action)": r"\bCAIR\b|COUNCIL ON AMERICAN.?ISLAMIC",
    "ISNA": r"\bISNA\b|ISLAMIC SOCIETY OF NORTH AMERICA",
    "NAIT": r"\bNAIT\b|NORTH AMERICAN ISLAMIC TRUST",
    "ICNA / ICNA Relief": r"\bICNA\b|ISLAMIC CIRCLE OF NORTH AMERICA",
    "Muslim American Society": r"MUSLIM AMERICAN SOCIETY|\bMAS[- ]?(PAC|YOUTH|FREEDOM)\b",
    "American Muslims for Palestine / AJP Action": r"AMERICAN MUSLIMS FOR PALESTINE|\bAJP\b|AMERICANS FOR JUSTICE IN PALESTINE",
    "Islamic Relief USA": r"ISLAMIC RELIEF|\bIRUSA\b",
    "Life for Relief and Development": r"LIFE FOR RELIEF",
    "Emgage / Emgage Action": r"\bEMGAGE\b",
    "MPower Change": r"MPOWER",
    "IMEU": r"\bIMEU\b|INSTITUTE FOR MIDDLE EAST UNDERSTANDING",
    "ACMER / MERIT PAC": r"\bACMER\b|AMERICAN COMMITTEE FOR MIDDLE EAST RIGHTS|MERIT PAC",
    "Unity & Justice Fund": r"UNITY (&|AND) JUSTICE",
    "Al-Awda": r"AL.?AWDA",
    "Arab American PAC (AAPAC)": r"\bAAPAC\b|ARAB AMERICAN POLITICAL ACTION",
    "Muslim Students Association": r"MUSLIM STUDENTS?.? ASSOCIATION|\bMSA NATIONAL\b",
    "Fiqh Council of North America": r"FIQH COUNCIL",
    "AMJA": r"\bAMJA\b|ASSEMBLY OF MUSLIM JURISTS",
    "USCMO": r"\bUSCMO\b|US COUNCIL OF MUSLIM ORGANIZATIONS",
    "Holy Land Foundation": r"HOLY LAND FOUNDATION",
    "IARA": r"\bIARA\b|ISLAMIC AMERICAN RELIEF|ISLAMIC AFRICAN RELIEF",
    "KindHearts": r"KINDHEARTS",
    "Islamic Association for Palestine": r"ISLAMIC ASSOCIATION FOR PALESTINE",
}
PATS = {org: re.compile(p, re.I) for org, p in ORGS.items()}


def orgs_in(*fields: str) -> list[str]:
    text = " | ".join(f or "" for f in fields)
    return [org for org, p in PATS.items() if p.search(text)]


rows = []
# campaign gifts as filed (gift-level employer/occupation)
for line in open(ROOT / "analysis" / "roster_named_itemized.jsonl", encoding="utf-8"):
    g = json.loads(line)
    if g.get("entity") != "IND":
        continue
    for org in orgs_in(g.get("employer"), g.get("occupation")):
        rows.append({"basis": "self_reported_employer", "org": org, "committee": "Abdul for U.S. Senate",
                     "donor": g["name"], "last_norm": g["last_norm"], "first_norm": g["first_norm"], "city": g["city"],
                     "state": g["state"], "zip5": (g.get("zip") or "")[:5], "date": g["date"], "amount": g["amt"],
                     "employer": g.get("employer"), "occupation": g.get("occupation"), "source": f"FEC {g['src']} tran {g['tran_id']}"})
# joint-committee shares and super PAC receipts (already in the claims tables)
CL = OUT
for name, committee_of in (("fec_rows", lambda r: r["committee"]), ("super_pac_receipts", lambda r: r["committee"])):
    p = CL / f"{name}.jsonl"
    if not p.exists():
        continue
    for r in map(json.loads, open(p, encoding="utf-8")):
        if name == "fec_rows" and r["kind"] != "joint_committee_share":
            continue
        if name == "super_pac_receipts" and r.get("entity_type") != "IND":
            continue
        for org in orgs_in(r.get("employer"), r.get("occupation")):
            rows.append({"basis": "self_reported_employer", "org": org, "committee": committee_of(r),
                         "donor": r.get("name_as_filed") or r.get("contributor"), "city": r["city"], "state": r["state"],
                         "date": r["date"], "amount": r["amount"], "employer": r.get("employer"),
                         "occupation": r.get("occupation"), "source": f"FEC file {r.get('fec_file_number') or r.get('file_number')}"})

# one row per donor x organization, with totals by committee
agg = defaultdict(lambda: {"amounts": defaultdict(float), "n_gifts": 0, "employers": set(), "occupations": set(), "sources": []})
for r in rows:
    k = (re.sub(r"\s+", " ", r["donor"].upper().replace(",  ", ", ")).strip(), r["city"].upper() if r["city"] else "", r["state"], r["org"])
    a = agg[k]
    a["amounts"][r["committee"]] += r["amount"] or 0
    a["n_gifts"] += 1
    a["employers"].add(r["employer"] or "")
    a["occupations"].add(r["occupation"] or "")
    a["sources"].append(r["source"])
out = []
for (donor, city, state, org), a in sorted(agg.items(), key=lambda kv: (kv[0][3], -sum(kv[1]["amounts"].values()))):
    out.append({"donor": donor, "city": city.title(), "state": state, "org": org, "basis": "self_reported_employer",
                "status": "confirmed (self-reported on the donor's own filing)",
                "role_as_filed": "; ".join(sorted(f"{o} / {e}" for o, e in zip(sorted(a["occupations"]), sorted(a["employers"])))),
                "employers_as_filed": "; ".join(sorted(e for e in a["employers"] if e)),
                "occupations_as_filed": "; ".join(sorted(o for o in a["occupations"] if o)),
                "total_by_committee": {k: round(v, 2) for k, v in a["amounts"].items()}, "n_gifts": a["n_gifts"],
                "sources": " | ".join(a["sources"][:20])})

# ---- step 2: organization rosters (officers, directors, staff, founders) matched to donors ---------------------------
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("sdn", ROOT / "scripts" / "sdn_screen.py")
sdn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdn)
CHAPTER_STATE = {"Michigan": "MI", "California": "CA", "Ohio": "OH", "Illinois": "IL", "Chicago": "IL", "Minnesota": "MN",
                 "Washington": "WA", "New York": "NY", "New Jersey": "NJ", "Pennsylvania": "PA", "Philadelphia": "PA",
                 "Florida": "FL", "Georgia": "GA", "Texas": "TX", "Arizona": "AZ", "Oklahoma": "OK", "Missouri": "MO",
                 "Kansas": "KS", "Connecticut": "CT", "Maryland": "MD", "Virginia": "VA", "North Carolina": "NC",
                 "Wisconsin": "WI", "Kentucky": "KY", "Alabama": "AL", "Nevada": "NV", "Massachusetts": "MA", "Iowa": "IA",
                 "Tennessee": "TN", "Oregon": "OR", "New Mexico": "NM", "Indiana": "IN", "Louisiana": "LA",
                 "South Carolina": "SC", "Utah": "UT"}


def parts(name: str) -> tuple[list[str], list[str]]:
    if "," in name:
        last, first = name.split(",", 1)
        return sdn.tokens(last), sdn.tokens(first)
    t = sdn.tokens(name)
    return (t[1:], t[:1]) if len(t) > 1 else ([], [])


def chapter_state(org: str) -> str:
    if not org.startswith("CAIR ") or org.startswith("CAIR ("):
        return ""
    return next((v for k, v in CHAPTER_STATE.items() if k in org and not (k == "Washington" and "D.C" in org)), "")


roster = [json.loads(l) for p in ROSTERS for l in open(p, encoding="utf-8") if l.strip()]
by_key = defaultdict(list)
for r in roster:
    lt, ft = parts(r["person"])
    if lt and ft:
        by_key[(lt[-1], ft[0])].append(r)
donor_pool = [{"name": d["name"], "city": d["city"], "state": d["state"], "committee": "Abdul for U.S. Senate", "amount": d["net"],
               "occupation": d["occupation"], "employer": d["employer"],
               "employers_all": " | ".join(d.get("employers_gross") or {})}
              for d in map(json.loads, open(ROOT / "analysis" / "donors_net.jsonl", encoding="utf-8"))]
sp = defaultdict(lambda: {"amount": 0.0})
if (OUT / "super_pac_receipts.jsonl").exists():
    for r in map(json.loads, open(OUT / "super_pac_receipts.jsonl", encoding="utf-8")):
        if r.get("entity_type") == "IND":
            k = (r["committee"], " ".join(r["contributor"].split()), r["city"], r["state"])
            sp[k]["amount"] += r["amount"] or 0
            sp[k].update(occupation=r["occupation"], employer=r["employer"])
donor_pool += [{"name": k[1], "city": k[2], "state": k[3], "committee": k[0], "amount": v["amount"],
                "occupation": v["occupation"], "employer": v["employer"], "employers_all": v["employer"] or ""}
               for k, v in sp.items()]
self_reported = {(r["donor"], r["org"]) for r in out}
matches = []
for d in donor_pool:
    lt, ft = parts(d["name"])
    if not lt or not ft:
        continue
    for r in by_key.get((lt[-1], ft[0]), []):
        org_family = next((o for o, pat in PATS.items() if pat.search(r["org"])), r["org"])
        own = bool(orgs_in(d["employers_all"], d["occupation"]) and org_family in orgs_in(d["employers_all"], d["occupation"]))
        same_city = bool(r.get("city") and d["city"] and r["city"].strip().upper() == d["city"].upper()
                         and (r.get("state") or "").strip().upper()[:2] == (d["state"] or ""))
        cs = chapter_state(r["org"])
        level = ("confirmed: the donor's own FEC employer/occupation names this organization" if own else
                 "candidate: same city as the record (identity review needed)" if same_city else
                 "candidate: chapter in the donor's state (identity review needed)" if cs and cs == d["state"] else
                 "name only: not a finding")
        matches.append({"donor": d["name"], "city": d["city"], "state": d["state"], "committee": d["committee"],
                        "amount": round(d["amount"] or 0, 2), "donor_occupation": d["occupation"], "donor_employer": d["employer"],
                        "org": r["org"], "role": r["role"], "role_kind": r["role_kind"], "years": r.get("years"),
                        "record_person": r["person"], "record_city": r.get("city"), "record_state": r.get("state"),
                        "source_kind": r["source_kind"], "source_url": r["source_url"], "sha256": r["sha256"],
                        "quote": r["quote"], "basis": "org_roster", "status": level})
with (OUT / "donor_org_roster_matches.jsonl").open("w", encoding="utf-8") as f:
    for m in matches:
        f.write(json.dumps(m, ensure_ascii=False) + "\n")
if matches:
    with (OUT / "donor_org_roster_matches.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(matches[0]))
        w.writeheader()
        w.writerows(matches)
lv = defaultdict(set)
for m in matches:
    lv[m["status"].split(":")[0] + ": " + m["status"].split(":")[1].split("(")[0].strip()].add((m["donor"], m["city"], m["org"]))
print(f"roster rows {len(roster)} | donors x roster-listing matches {len(matches)} | distinct donor-org pairs by level: "
      + "; ".join(f"{k} {len(v)}" for k, v in sorted(lv.items())))

with (OUT / "donor_org_roles.jsonl").open("w", encoding="utf-8") as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
with (OUT / "donor_org_roles.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]) if out else ["donor"])
    w.writeheader()
    for r in out:
        w.writerow({k: json.dumps(v) if isinstance(v, dict) else v for k, v in r.items()})
by_org = defaultdict(int)
for r in out:
    by_org[r["org"]] += 1
print(f"self-reported employer rows {len(rows)} -> donors x orgs {len(out)}: {dict(sorted(by_org.items(), key=lambda kv: -kv[1]))}")
