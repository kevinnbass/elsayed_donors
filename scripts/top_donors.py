"""Rank individual donors overall and by occupation sector, net of refunds and reattributions.

Gross roster rows (analysis/roster_named_itemized.jsonl) overstate some donors: an
excessive gift stays on Schedule A while its fix is filed elsewhere. Per-donor net is

    non-memo SA11AI + memo-X SA11AI (IND reattributions / redesignations, +/-)
    + memo-X SA12 IND (the donor's share of a joint fundraising committee transfer) - SB20A refunds

read from the same e-files as the roster. A joint-committee share counts toward the donor's limit
and the committee's own running total includes it, so it is part of the donor's net. The 2025-26 limit is $3,500 per election
($7,000 for primary + general), so a correct net total never exceeds $7,000.

Donor key is last + first + suffix + ZIP5 + house number. The same name at another ZIP or
another house number is NOT merged (identity unproven; a mover splits rather than two people
merging); it is reported next to the donor instead.

Control: the committee's own cycle-to-date aggregate (Schedule A column 22) on each
donor's last receipt, less refunds dated after it, must equal the computed net.

Top 100: everyone at or above the $7,000 maximum is tied, so the 100 are drawn from them
at random. The draw orders the pool by sha256(SEED|last|first|suffix|ZIP5), so anyone can
re-run it and get the same 100, and it does not depend on file order.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILINGS = ROOT / "data" / "filings"
ROSTER = ROOT / "analysis" / "roster_named_itemized.jsonl"
OUT_JSON = ROOT / "analysis" / "top_donors.json"
OUT_TXT = ROOT / "analysis" / "TOP100_and_by_sector.txt"
OUT_ALL = ROOT / "analysis" / "donors_net.jsonl"
OUT_NAMES = ROOT / "analysis" / "TOP100_names.txt"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sector_breakdown import sector  # noqa: E402

THROUGH = "Sep 30, 2026"  # coverage end of the latest report in data/filings
CAP = 7000.0
N_TOP = 20
N_SAMPLE = 100
SEED = "elsayed-top100-2026-10-16"

# FEC 8.5 Schedule A / B columns (0-based)
TRAN, ENTITY, LAST, FIRST, SUFFIX, STREET1, CITY, STATE, ZIP, ELEC, DATE, AMT, AGGR, EMP, OCC = (
    2, 5, 7, 8, 11, 12, 14, 15, 16, 17, 19, 20, 21, 23, 24)


def norm_token(s: str) -> str:
    s = (s or "").upper().replace("'", "").replace(".", "")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def house_number(street: str) -> str:
    m = re.match(r"\s*(?:P\.?\s*O\.?\s*BOX\s*)?(\d+)", (street or "").upper())
    return m.group(1) if m else ""


def key_of(last: str, first: str, suffix: str, zip_: str, street: str) -> tuple[str, str, str, str, str]:
    return (norm_token(last), norm_token(first), norm_token(suffix), (zip_ or "")[:5], house_number(street))


def load_filings() -> tuple[dict, list, list, list]:
    """SA11AI rows by (filing, tran_id); memo IND rows; joint-committee memo IND rows; SB20A refunds."""
    sa, memo, jfc, refunds = {}, [], [], []
    for p in sorted(FILINGS.glob("*.csv")):
        num = re.search(r"(\d{7})\.csv$", p.name).group(1)
        with p.open(encoding="utf-8", errors="replace", newline="") as f:
            for r in csv.reader(f):
                if r[0] == "SA11AI":
                    is_memo = "X" in r[25:]
                    if is_memo and r[ENTITY] == "IND":
                        memo.append((num, r))
                    elif not is_memo:
                        sa[(num, r[TRAN])] = r
                elif r[0] == "SA12" and "X" in r[25:] and r[ENTITY] == "IND":
                    jfc.append((num, r))
                elif r[0] == "SB20A":
                    refunds.append((num, r))
    return sa, memo, jfc, refunds


def money(x: float) -> str:
    return f"${x / 1e6:.2f}M" if x >= 1e6 else f"${x / 1e3:,.0f}k"


def line(r: dict) -> str:
    return f"{r['name']} — ${r['net']:,.0f} — {r['occupation'] or '—'}"


def render_txt(out: dict) -> str:
    n_cap = out["n_at_cap"]
    lines = [
        f"Top donors, overall and by occupation sector (named itemized $, Jan 1 2025 – {THROUGH})",
        "Net of refunds and of the committee's reattributions to a spouse or household member;",
        "includes each donor's share of joint fundraising committee transfers.",
        "One person may give at most $7,000 ($3,500 primary + $3,500 general).",
        "",
        "Overall top 100",
        f"{n_cap} donors gave $7,000 or more, so any overall top 20 or top 100 is a {n_cap}-way tie.",
        f"These 100 are drawn at random from the {n_cap} (seed \"{SEED}\"; see scripts/top_donors.py).",
        "Every one of them is listed under their sector further down.",
        "",
    ]
    lines += [line(r) for r in out["top100_random_from_cap"]["donors"]]
    lines += [
        "",
        f"Above $7,000: {out['n_over_cap']} donors, per the committee's own running totals as of the {THROUGH} report",
        f"(an excess has 60 days to be refunded; refunds after {THROUGH} are in later reports):",
        "",
    ]
    lines += [line(r) for r in out["over_cap"]]
    lines += ["", "By sector (the occupation carrying most of a donor's dollars)", ""]
    for s in out["sectors"]:
        lines.append(f"{s['sector']} — {s['n_donors']:,} donors — {money(s['net'])} — "
                     f"{s['n_at_cap']} at the $7,000 maximum")
        if s["n_at_cap"] >= N_TOP:
            lines.append(f"All {s['n_at_cap']} at the maximum (above $7,000 first, then A–Z):")
            lines += [line(r) for r in out["donors_at_cap"] if r["sector"] == s["sector"]]
        else:
            lines += [line(r) for r in s["top20"]]
            if s["top20_cut_is_tie"]:
                lines.append(f"(more donors tied at ${s['top20'][-1]['net']:,.0f})")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    sa, memo, jfc, refunds = load_filings()
    donors: dict = defaultdict(lambda: {
        "gross": 0.0, "reattrib": 0.0, "jfc": 0.0, "refunded": 0.0, "n_gifts": 0, "n_jfc": 0,
        "sector_amt": defaultdict(float), "occs": defaultdict(float), "emps": defaultdict(float),
        "events": [],  # (date, kind, amt, aggr)
        "name": "", "city": "", "state": "",
    })
    org_amt = 0.0
    with ROSTER.open(encoding="utf-8") as f:
        for line in f:
            g = json.loads(line)
            num = re.search(r"(\d{7})$", g["src"]).group(1)
            r = sa[(num, g["tran_id"])]
            if g["entity"] != "IND":
                org_amt += g["amt"]
                continue
            d = donors[key_of(r[LAST], r[FIRST], r[SUFFIX], r[ZIP], r[STREET1])]
            d["gross"] += g["amt"]
            d["n_gifts"] += 1
            d["sector_amt"][sector(g.get("occupation") or "", g.get("employer") or "")] += g["amt"]
            if (g.get("occupation") or "").strip():
                d["occs"][g["occupation"].strip()] += g["amt"]
            if (g.get("employer") or "").strip():
                d["emps"][g["employer"].strip()] += g["amt"]
            d["events"].append((r[DATE], "sa", g["amt"], float(r[AGGR] or 0), num))
            if r[DATE] >= max(e[0] for e in d["events"]):
                d["name"], d["city"], d["state"] = g["name"], g["city"], g["state"]

    for num, r in memo:
        d = donors[key_of(r[LAST], r[FIRST], r[SUFFIX], r[ZIP], r[STREET1])]
        amt = float(r[AMT])
        d["reattrib"] += amt
        d["events"].append((r[DATE], "memo", amt, float(r[AGGR] or 0), num))
        if not d["n_gifts"]:
            # household member a gift was reattributed to, with no gift of their own
            d["name"], d["city"], d["state"] = f"{r[LAST]}, {r[FIRST]}", r[CITY], r[STATE]
            d["sector_amt"][sector(r[OCC], r[EMP])] += abs(amt)
            if r[OCC].strip():
                d["occs"][r[OCC].strip()] += abs(amt)

    for num, r in jfc:
        d = donors[key_of(r[LAST], r[FIRST], r[SUFFIX], r[ZIP], r[STREET1])]
        amt = float(r[AMT])
        d["jfc"] += amt
        d["n_jfc"] += 1
        d["sector_amt"][sector(r[OCC], r[EMP])] += amt
        if r[OCC].strip():
            d["occs"][r[OCC].strip()] += amt
        if r[EMP].strip():
            d["emps"][r[EMP].strip()] += amt
        d["events"].append((r[DATE], "jfc", amt, float(r[AGGR] or 0), num))
        if not d["n_gifts"] and not d["name"]:
            d["name"], d["city"], d["state"] = f"{r[LAST]}, {r[FIRST]}", r[CITY], r[STATE]

    unmatched_refunds, org_refunds = [], []
    for num, r in refunds:
        if r[ENTITY] != "IND":  # a corporate gift returned; corporate gifts are outside the individual totals
            org_refunds.append({"org": r[6], "zip": r[ZIP], "amt": float(r[AMT])})
            continue
        k = key_of(r[LAST], r[FIRST], r[SUFFIX], r[ZIP], r[STREET1])
        if k not in donors:
            unmatched_refunds.append({"name": f"{r[LAST]}, {r[FIRST]}", "zip": r[ZIP], "amt": float(r[AMT])})
            continue
        donors[k]["refunded"] += float(r[AMT])
        donors[k]["events"].append((r[DATE], "refund", float(r[AMT]), None, num))

    # same name + state, different ZIP: shown, never merged
    by_name_state = defaultdict(list)
    for k, d in donors.items():
        by_name_state[(k[0], k[1], k[2], d["state"])].append(k)

    rows = []
    for k, d in donors.items():
        net = round(d["gross"] + d["reattrib"] + d["jfc"] - d["refunded"], 2)
        # The committee aggregate is as of its report: refunds in the same filing are already
        # in it, refunds in a later filing are not.
        # A joint-committee row's aggregate is sometimes the donor's combined running total and
        # sometimes the joint committee's own, so a donor with both kinds of receipts is checked
        # against max(direct, joint) and direct + joint (1,210 and 10 of 1,241 such donors fit).
        def last_aggregate(kinds: tuple[str, ...]) -> float | None:
            rs = sorted([e for e in d["events"] if e[1] in kinds], key=lambda e: (e[4], e[0]))
            if not rs:
                return None
            last = rs[-1]
            aggr = max(e[3] for e in rs if (e[4], e[0]) == (last[4], last[0]))
            return aggr - sum(e[2] for e in d["events"] if e[1] == "refund" and e[4] > last[4])

        direct, joint = last_aggregate(("sa", "memo")), last_aggregate(("jfc",))
        candidates = [c for c in (direct, joint) if c is not None]
        if direct is not None and joint is not None:
            candidates = [max(direct, joint), direct + joint]
        gaps = [round(c - net, 2) for c in candidates]
        committee = round(candidates[0], 2)
        if any(abs(g) < 0.01 for g in gaps):
            check = "exact"
        elif any(0 < g <= 200 for g in gaps):
            check = "unitemized_gap"  # aggregate also counts early gifts under the $200 itemization line
        else:
            check = "differs"
        sec_amt = d["sector_amt"]
        sec = max(sec_amt, key=lambda s: sec_amt[s]) if sec_amt else "Blank / unknown occupation"
        others = [o for o in by_name_state[(k[0], k[1], k[2], d["state"])] if o != k]
        rows.append({
            "name": d["name"],
            "last_norm": k[0],
            "first_norm": k[1],
            "suffix": k[2],
            "city": d["city"],
            "state": d["state"],
            "zip5": k[3],
            "house": k[4],
            "net": net,
            "gross": round(d["gross"], 2),
            "reattributed": round(d["reattrib"], 2),
            "joint_committee": round(d["jfc"], 2),
            "refunded": round(d["refunded"], 2),
            "n_gifts": d["n_gifts"],
            "occupation": max(d["occs"], key=d["occs"].get) if d["occs"] else "",
            "employer": max(d["emps"], key=d["emps"].get) if d["emps"] else "",
            "employers_gross": {e: round(a, 2) for e, a in d["emps"].items()},
            "sector": sec,
            "committee_aggregate": committee,
            "committee_check": check,
            "same_name_state_other_zip": [
                {"zip5": o[3], "house": o[4], "net": round(donors[o]["gross"] + donors[o]["reattrib"] + donors[o]["jfc"]
                                            - donors[o]["refunded"], 2)}
                for o in others
            ],
        })

    rows.sort(key=lambda r: (-r["net"], r["name"]))
    total_net = sum(r["net"] for r in rows)
    maxed = [r for r in rows if r["net"] >= CAP - 0.005]
    over = [r for r in rows if r["net"] > CAP + 0.005]
    checks: dict = defaultdict(int)
    for r in rows:
        checks[r["committee_check"]] += 1
    differs = [r for r in rows if r["committee_check"] == "differs"]

    def draw_key(r: dict) -> str:
        return hashlib.sha256(
            f"{SEED}|{r['last_norm']}|{r['first_norm']}|{r['suffix']}|{r['zip5']}|{r['house']}".encode()).hexdigest()

    sample = sorted(sorted(maxed, key=draw_key)[:N_SAMPLE], key=lambda r: r["name"])

    sectors = defaultdict(list)
    for r in rows:
        sectors[r["sector"]].append(r)
    sector_out = []
    for name, rs in sorted(sectors.items(), key=lambda kv: -sum(r["net"] for r in kv[1])):
        sector_out.append({
            "sector": name,
            "net": round(sum(r["net"] for r in rs), 2),
            "n_donors": len(rs),
            "n_at_cap": sum(1 for r in rs if r["net"] >= CAP - 0.005),
            "top20": rs[:N_TOP],
            "top20_cut_is_tie": len(rs) > N_TOP and rs[N_TOP - 1]["net"] == rs[N_TOP]["net"],
        })

    out = {
        "method": __doc__.strip().splitlines()[0],
        "cap_per_cycle": CAP,
        "n_individual_donors": len(rows),
        "individual_net_total": round(total_net, 2),
        "org_rows_excluded_amt": round(org_amt, 2),
        "joint_committee_attributed": round(sum(d["jfc"] for d in donors.values()), 2),
        "n_donors_joint_committee_only": sum(1 for d in donors.values() if d["n_jfc"] and not d["n_gifts"]),
        "n_at_cap": len(maxed),
        "n_over_cap": len(over),
        "over_cap": over,
        "unmatched_refunds": unmatched_refunds,
        "refunds_to_organizations": org_refunds,
        "control_committee_aggregate": dict(checks),
        "control_differs_rows": differs,
        "top100_random_from_cap": {
            "seed": SEED,
            "rule": "order the at-or-above-$7,000 pool by sha256(seed|last|first|suffix|zip5|house); take 100",
            "pool": len(maxed),
            "donors": sample,
        },
        "donors_at_cap": maxed,
        "sectors": sector_out,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    OUT_TXT.write_text(render_txt(out), encoding="utf-8")
    OUT_NAMES.write_text("\n".join(r["name"] for r in sample) + "\n", encoding="utf-8")
    with OUT_ALL.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    print(f"individual donors {len(rows):,}  net ${total_net:,.2f}  (ORG rows excluded ${org_amt:,.2f})")
    print(f"at $7,000 cap: {len(maxed)}   over cap: {len(over)}   unmatched refunds: {len(unmatched_refunds)}")
    print("control vs committee aggregate:", dict(checks))
    for r in differs:
        if r["net"] >= 3500:
            print("  DIFFERS", r["name"], r["zip5"], "net", r["net"], "committee", r["committee_aggregate"])
    for s in sector_out:
        print(f"{s['sector']}: net ${s['net']:,.0f}  donors {s['n_donors']:,}  at cap {s['n_at_cap']}"
              f"  #20 ${s['top20'][-1]['net']:,.0f}  tie-at-cut {s['top20_cut_is_tie']}")


if __name__ == "__main__":
    main()
