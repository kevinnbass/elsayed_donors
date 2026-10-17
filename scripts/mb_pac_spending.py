"""Super PAC report summaries and independent expenditures, as filed, for the money-flow figures.

Usage: python3 -I scripts/mb_pac_spending.py <pull_dir> [out_dir]
  <pull_dir>: an OpenFEC pull made by fec_pull_spend.py (ffm_/unity_ {reports,E}.json)
  out_dir: default analysis/private/mb_claims
Writes super_pac_reports.jsonl/.csv (the most recent version of each report) and super_pac_spending.jsonl/.csv (every
schedule E row, with `counts` and `basis`). A row counts toward spending when it is a non-memo line of the most recent
version of a regular report (F3X), or, for spending dated after the committee's last F3X coverage date, a line of the
most recent version of a 24- or 48-hour notice (F24), whose amounts are not yet on any regular report. No row is dropped.
Prints, per committee, the reconciliation of counted F3X lines against each report's independent-expenditure total.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PULL = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "analysis" / "private" / "mb_claims"
COMMITTEES = {"ffm": ("Fighting for Michigan PAC", "C00919373"), "unity": ("Unity & Justice Fund", "C00881011")}
SINCE = "2025-01-01"   # the 2025-26 cycle, the same window as the schedule A pull


def money(r: dict, k: str) -> float:
    return round(float(r.get(k) or 0), 2)


reports, spending = [], []
for key, (committee, cid) in COMMITTEES.items():
    reps = [r for r in json.load(open(PULL / f"{key}_reports.json")) if r.get("most_recent")
            and (r["coverage_start_date"] or "")[:10] >= SINCE]
    for r in sorted(reps, key=lambda r: r["coverage_start_date"]):
        ie, op = money(r, "independent_expenditures_period"), money(r, "total_operating_expenditures_period")
        contrib = money(r, "fed_candidate_committee_contributions_period")
        other, refunds = money(r, "other_disbursements_period"), money(r, "total_contribution_refunds_period")
        disb = money(r, "total_disbursements_period")
        reports.append({"committee": committee, "committee_id": cid, "report_type": r["report_type"],
                        "coverage_start": r["coverage_start_date"][:10], "coverage_end": r["coverage_end_date"][:10],
                        "receipt_date": (r.get("receipt_date") or "")[:10], "file_number": r["file_number"],
                        "total_receipts": money(r, "total_receipts_period"), "independent_expenditures": ie,
                        "operating_expenditures": op, "contributions_to_candidates_and_committees": contrib,
                        "other_disbursements": other, "contribution_refunds": refunds, "total_disbursements": disb,
                        "unexplained_disbursements": round(disb - ie - op - contrib - other - refunds, 2),
                        "cash_on_hand_beginning": money(r, "cash_on_hand_beginning_period"),
                        "cash_on_hand_end": money(r, "cash_on_hand_end_period"), "debts_owed_by": money(r, "debts_owed_by_committee")})
    current = {r["file_number"] for r in reps}
    last_end = max(r["coverage_end_date"][:10] for r in reps)
    for r in json.load(open(PULL / f"{key}_E.json"))["processed"]:
        when = (r.get("expenditure_date") or r.get("dissemination_date") or "")[:10]
        if r["filing_form"] == "F3X":
            counts = r["file_number"] in current and r.get("memo_code") != "X"
            basis = ("regular report, most recent version" if counts else
                     "memo line (not in the report's totals)" if r["file_number"] in current else "superseded or out-of-cycle report")
        else:
            counts = when > last_end and bool(r.get("most_recent"))
            basis = ("notice after the last regular report" if counts else
                     "notice covered by a regular report" if when <= last_end else "superseded notice")
        spending.append({"committee": committee, "form": r["filing_form"], "report_type": r.get("report_type"),
                         "file_number": r["file_number"], "transaction_id": r["transaction_id"],
                         "expenditure_date": when, "dissemination_date": (r.get("dissemination_date") or "")[:10],
                         "amount": money(r, "expenditure_amount"), "support_oppose": r.get("support_oppose_indicator"),
                         "candidate": r.get("candidate_name"), "candidate_id": r.get("candidate_id"),
                         "candidate_party": r.get("candidate_party"), "candidate_state": r.get("candidate_office_state"),
                         "payee": r.get("payee_name"), "description": r.get("expenditure_description"),
                         "memo_code": r.get("memo_code"), "filed": (r.get("filing_date") or "")[:10],
                         "counts": counts, "basis": basis, "last_regular_report_end": last_end})
    # reconciliation: counted F3X lines against each report's line-24 total
    by_file = defaultdict(float)
    for s in spending:
        if s["committee"] == committee and s["counts"] and s["form"] == "F3X":
            by_file[s["file_number"]] += s["amount"]
    for r in [x for x in reports if x["committee"] == committee and x["independent_expenditures"]]:
        gap = round(r["independent_expenditures"] - by_file.get(r["file_number"], 0), 2)
        print(f"{committee} {r['report_type']} {r['coverage_end']}: report {r['independent_expenditures']:,.2f}, lines "
              f"{by_file.get(r['file_number'], 0):,.2f}, gap {gap:,.2f}")
    rs = [x for x in reports if x["committee"] == committee]
    first = min(rs, key=lambda x: x["coverage_start"])
    drift = round(first["cash_on_hand_beginning"] + sum(x["total_receipts"] for x in rs)
                  - sum(x["total_disbursements"] for x in rs) - max(rs, key=lambda x: x["coverage_end"])["cash_on_hand_end"], 2)
    print(f"{committee}: {len(rs)} reports through {last_end}; cash identity drift {drift:,.2f}; disbursements not in a "
          f"reported category {sum(x['unexplained_disbursements'] for x in rs):,.2f}")


def dump(name: str, rows: list[dict]) -> None:
    with (OUT / f"{name}.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (OUT / f"{name}.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


dump("super_pac_reports", reports)
dump("super_pac_spending", spending)
print(f"reports {len(reports)} | spending rows {len(spending)} (counted {sum(s['counts'] for s in spending)}) | source {PULL}")
