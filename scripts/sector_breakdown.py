"""Rank named-itemized dollars by occupation sector."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "analysis" / "roster_named_itemized.jsonl"

# Occupation rules, first match wins. Short tokens are whole words (IT, RN, MD, DO, ...):
# substring matches put "Nonprofit" in tech and "Contractor" in media. Physician status
# comes from the occupation only, never the employer (the employer fallback below is
# health-care staff). Rules revised Oct 16, 2026; see README "Sector rules".
PHYSICIAN = re.compile(
    r"PHYSICIANS?\b|PHYSCIAN|PHYSICAN|PHYSICAIN|PHYAICIAN|PHYASIXIAN|PHYSIXIAN|\bDOCTOR\b|"
    r"SURGEON|\bM\.? ?D\b|\bD\.O\b|\bDO\b|CARDIOLOG|ONCOLOG|PEDIATRICIAN|PSYCHIATR|ANESTHESI|"
    r"RADIOLOG|NEUROLOG|DERMATOLOG|HOSPITALIST|INTENSIVIST|INTERNIST|PATHOLOGIST|OB.?GYN|"
    r"ORTHOPA?ED|OPHTHALM|NEPHROLOG|RHEUMATOL|GASTROENTER|PULMONOLOG|ENDOCRIN|UROLOG|"
    r"NEONATOL|NEUROSURG|(INTERNAL|FAMILY|EMERGENCY) MEDICINE", re.I)
# a physician word in these titles names someone else's job
NOT_PHYSICIAN = re.compile(
    r"ASSISTANT|PHYSICIAN ASSOCIATE|TECHNOLOGIST|TECHNICIAN|\bTECH\b|SOCIAL WORK|\bNURS|SCRIBE|"
    r"BILLER|BILLING|DENTIST|DENTAL|ORTHODONT|PHARM|CHIROPRACT|NATUROPATH|VETERIN|PSYCHOLOG", re.I)
NOT_EMPLOYED = re.compile(
    r"NOT[ -]EMPLOYED|UNEMPLOYED|RETIRED|^NONE$|^N/?A$|HOME ?MAKER|STAY AT HOME|"
    r"STUDENTS?$|DISABLED", re.I)
HEALTH_STAFF_OCC = re.compile(
    r"HEALTH ?CARE|\bMEDICAL\b|\bHOSPITALS?\b|CLINICAL|PUBLIC HEALTH|EPIDEMIOLOG|\bCMO\b|"
    r"CHIEF MEDICAL|RADIOLOG|SONOGRAPH|PHLEBOTOM", re.I)
HEALTH_EMPLOYER = re.compile(
    r"HEALTH ?CARE|\bHEALTH\b|\bMEDICAL\b|\bMEDICINE\b|\bHOSPITALS?\b|\bCLINICS?\b|"
    r"KAISER|PERMANENTE|\bTPMG\b|COREWELL|BEAUMONT|MCLAREN|PROMEDICA|ASCENSION|"
    r"CARDIOLOG|ONCOLOG|DERMATOLOG|RADIOLOG|PEDIATRIC|ORTHOPA?ED|PHYSICIANS\b|SURGERY|SURGICAL", re.I)

HC_PHYS = "Healthcare — physician / surgeon / specialist"
HC_CLIN = "Healthcare — other clinician (dentist, pharmacist, nurse, etc.)"
HC_STAFF = "Healthcare — hospital / system / 'healthcare' staff"
NOT_EMP = "Not employed / retired / student"

RULES: list[tuple[str, re.Pattern[str]]] = [
    (HC_CLIN, re.compile(
        r"DENTIST|DENTAL|\bDDS\b|\bDMD\b|ORTHODONT|PHARMACIST|PHARM\.?D|\bNURS(E|ES|ING)\b|"
        r"\bR\.?N\b|\bLPN\b|\bNP\b|\bDNP\b|CRNA|PHYS\w* ASSISTANT|PHYSICIAN ASSOCIATE|\bPA-?C\b|"
        r"PSYCHOLOGIST|PSYCHOANALYST|THERAPIST|CHIROPRACT|OPTOMETR|SOCIAL WORK|VETERINAR|"
        r"NATUROPATH|(MENTAL HEALTH|\bMH|ADDICTION) COUNSELOR|\bLPC\b|MIDWIFE|PARAMEDIC|"
        r"\bEMT\b|DIETITIAN|AUDIOLOG", re.I)),
    (HC_STAFF, HEALTH_STAFF_OCC),
    (NOT_EMP, NOT_EMPLOYED),
    ("Law", re.compile(
        r"ATTORNEY|LAWYER|LEGAL|\bCOUNSEL\b|JUDGE|LAW PROFESSOR|PARALEGAL|\bLAW\b(?! ENFORCEMENT)", re.I)),
    ("Tech / engineering", re.compile(
        r"ENGINEER|SOFTWARE|PROGRAMMER|DEVELOPER|DATA SCIEN|PRODUCT MANAGER|TECHNOLOG|\bIT\b|"
        r"COMPUTER|\bSRE\b|DEVOPS|\bSWE\b|MACHINE LEARNING|\bAI\b|TECHNICAL STAFF|"
        r"TECHNICAL PROGRAM|\bTPM\b", re.I)),
    ("Education / academic", re.compile(
        r"PROFESSOR|TEACHER|EDUCATOR|LECTURER|ACADEMIC|UNIVERSITY|FACULTY|"
        r"^(ASSISTANT |VICE |SCHOOL )?PRINCIPAL$|SCHOOL PRINCIPAL|\bSCHOOLS?\b|\bDEAN\b|"
        r"LIBRARIAN|(GUIDANCE|SCHOOL) COUNSELOR|\bTUTOR", re.I)),
    ("Finance / investing", re.compile(
        r"FINANCE|FINANCIAL|INVEST|BANKER|BANKING|\bANALYSTS?\b|ACCOUNTANT|\bCPA\b|HEDGE|"
        r"PRIVATE EQUITY|VENTURE|WEALTH|TRADER|\bCFO\b|UNDERWRITER|CAPITAL MARKETS|ASSET MANA|"
        r"ACTUAR|\bAUDIT", re.I)),
    ("Business owner / executive / consultant (non-health)", re.compile(
        r"\bCEO\b|FOUNDER|\bOWNER\b|PRESIDENT|EXECUTIVE|CONSULT|CONSLUTANT|ENTREPRENEUR|ENTREPENEUR|"
        r"MANAGING DIR|\bPARTNERS?\b|DIRECTOR|MANAGER|MANAGEMENT|SELF[ -]EMPLOY|BUSINESS|"
        r"CHAIRMAN|\bCOO\b|\bCTO\b|\bCIO\b|CHIEF \w+ OFFICER|MANAGING MEMBER|\bHR\b|"
        r"HUMAN RESOURCES|ADVISOR|STRATEGIST", re.I)),
    ("Government / politics / nonprofit", re.compile(
        r"GOVERNMENT|\bGOVT\b|PUBLIC SERV|CIVIL SERV|ORGANIZER|ACTIVIST|NON-?PROFIT|NON PROFIT|"
        r"POLICY|CAMPAIGN|UNION (ORGANIZER|STAFF|REP)|POLICE|LAW ENFORCEMENT|FIREFIGHTER|LEGISLAT|COUNCIL MEMBER|"
        r"FUNDRAIS|ADVOCATE|PATENT EXAMINER|POSTAL|RURAL CARRIER", re.I)),
    ("Media / arts / other professional", re.compile(
        r"\b(SCREEN|COPY|SPEECH|GHOST)?WRITERS?\b|JOURNALIST|ARTIST|\bACTOR\b|\bACTRESS\b|"
        r"DESIGNER|ARCHITECT|MARKETING|\bSALES\b|SALES(MAN|WOMAN|PERSON)|REAL ?ESTATE|REALTOR|"
        r"FARMER|MUSICIAN|FILMMAKER|PRODUCER|PODCAST|AUTHOR|COMPOSER|PUBLISHER|PHOTOGRAPH|"
        r"\bEDITOR\b|REPORTER|COMEDIAN", re.I)),
]

NO_OCCUPATION = {"", "NULL", "INFORMATION REQUESTED", "INFO REQUESTED", "REQUESTED",
                 "NONE OF YOUR BUSINESS"}
# occupation and employer typed into each other's boxes ("Sutter" / "Physician")
SWAPPED_TITLE = re.compile(r"PHYSICIANS?|DOCTOR|SURGEON|M\.? ?D\.?|NURSE|R\.?N\.?|DENTIST|PHARMACIST", re.I)


def sector(occ: str, emp: str) -> str:
    o = (occ or "").strip()
    if o.upper() in NO_OCCUPATION:
        return HC_STAFF if HEALTH_EMPLOYER.search(emp or "") else "Blank / unknown occupation"
    if PHYSICIAN.search(o) and not NOT_PHYSICIAN.search(o):
        return HC_PHYS
    for name, pat in RULES:
        if name == NOT_EMP and HEALTH_EMPLOYER.search(emp or "") and not pat.search(o):
            return HC_STAFF  # employer fallback: anyone working for a health employer
        if pat.search(o):
            return name
    if SWAPPED_TITLE.fullmatch((emp or "").strip()):
        return sector(emp, o)
    return "Other / unclassified"


def main() -> None:
    tot = 0.0
    n = 0
    buckets = defaultdict(lambda: {"n": 0, "amt": 0.0})
    occ_in = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
    with ROSTER.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            tot += r["amt"]
            n += 1
            s = sector(r.get("occupation") or "", r.get("employer") or "")
            buckets[s]["n"] += 1
            buckets[s]["amt"] += r["amt"]
            occ_in[s][(r.get("occupation") or "").strip() or "(blank)"][0] += 1
            occ_in[s][(r.get("occupation") or "").strip() or "(blank)"][1] += r["amt"]

    ranked = sorted(buckets.items(), key=lambda kv: -kv[1]["amt"])
    out = {
        "named_itemized_total": round(tot, 2),
        "n_gifts": n,
        "sectors": [],
    }
    print(f"Named itemized ${tot:,.2f}  n={n}\n")
    for i, (name, b) in enumerate(ranked, 1):
        pct = 100.0 * b["amt"] / tot
        rec = {
            "rank": i,
            "sector": name,
            "amt": round(b["amt"], 2),
            "pct": round(pct, 1),
            "n_gifts": b["n"],
            "top_occupations": [
                {"occ": o, "n": c, "amt": round(a, 2)}
                for o, (c, a) in sorted(occ_in[name].items(), key=lambda kv: -kv[1][1])[:6]
            ],
        }
        out["sectors"].append(rec)
        print(f"{i}. {name} — ${b['amt']:,.0f} — {pct:.1f}% — {b['n']:,} gifts")
        for o in rec["top_occupations"][:3]:
            print(f"      {o['occ']}: ${o['amt']:,.0f}")

    # healthcare rollup
    hc = [s for s in out["sectors"] if s["sector"].startswith("Healthcare")]
    hc_amt = sum(s["amt"] for s in hc)
    print(f"\nHEALTHCARE COMBINED — ${hc_amt:,.0f} — {100*hc_amt/tot:.1f}%")
    out["healthcare_combined"] = {
        "amt": round(hc_amt, 2),
        "pct": round(100.0 * hc_amt / tot, 1),
    }
    dest = ROOT / "analysis" / "sector_breakdown.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("WROTE", dest)


if __name__ == "__main__":
    main()
