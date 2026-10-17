"""Build the named itemized roster (Form 3 line 11a(i)) from the current F3 e-filings.

Usage: python scripts/build_roster.py [filing.csv ...]
With no arguments it reads every data/filings/*.csv (the most recent version of each report;
superseded amendments live in data/filings/superseded/ and are not read).

Same parse as scripts/recompute/elsayed_nppes_and_q1.py::parse_sa11ai: Schedule A line 11a(i)
rows, memo-X rows dropped. Each report's rows must sum to that report's own line 11a(i) period
total on its F3 summary row; the cycle total is the sum of the reports. (The committee's
year-to-date column has drifted from the sum of its own reports since 2025 and is not used.)

Writes analysis/roster_named_itemized.jsonl and analysis/roster_summary.json, or, when files
are given on the command line, only prints the summary (used for the reproduction control).
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILINGS = ROOT / "data" / "filings"
OUT = ROOT / "analysis" / "roster_named_itemized.jsonl"
SUMMARY = ROOT / "analysis" / "roster_summary.json"

I_ENTITY, I_LAST, I_FIRST = 5, 7, 8
I_CITY, I_ST, I_ZIP = 14, 15, 16
I_DATE, I_AMT, I_EMP, I_OCC = 19, 20, 23, 24
F3_LINE_11AI_PERIOD = 32  # FEC 8.5 F3 summary row: column A, line 11(a)(i); checked on all 9 filings


def norm_token(s: str) -> str:
    s = (s or "").upper()
    s = s.replace("'", "").replace(".", "")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def split_fec_name(name: str) -> tuple[str, str]:
    name = (name or "").strip()
    if "," in name:
        last, rest = name.split(",", 1)
    else:
        parts = name.split()
        last, rest = (parts[0] if parts else ""), " ".join(parts[1:])
    first = rest.strip().split()[0] if rest.strip() else ""
    return norm_token(last), norm_token(first)


def parse(path: Path) -> tuple[list[dict], float | None]:
    src = path.stem
    text = path.read_bytes().decode("latin-1", errors="replace")
    out, f3_11ai = [], None
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        if row[0].startswith("F3") and len(row) > F3_LINE_11AI_PERIOD:
            f3_11ai = float(row[F3_LINE_11AI_PERIOD] or 0)
        if row[0] != "SA11AI" or len(row) < 25:
            continue
        memo_cd = ((row[42] if len(row) > 42 else "") or (row[41] if len(row) > 41 else "")).strip()
        if memo_cd.upper() == "X":
            continue
        try:
            amt = float(row[I_AMT] or 0)
        except ValueError:
            amt = 0.0
        last = (row[I_LAST] or "").strip()
        first = (row[I_FIRST] or "").strip()
        name = f"{last}, {first}".strip(", ")
        last_n, first_n = split_fec_name(name)
        out.append({
            "src": src,
            "tran_id": row[2] if len(row) > 2 else "",
            "name": name,
            "last_norm": last_n,
            "first_norm": first_n,
            "city": (row[I_CITY] or "").strip(),
            "state": (row[I_ST] or "").strip().upper(),
            "zip": (row[I_ZIP] or "").strip(),
            "date": (row[I_DATE] or "").strip(),
            "amt": amt,
            "employer": (row[I_EMP] or "").strip(),
            "occupation": (row[I_OCC] or "").strip(),
            "entity": (row[I_ENTITY] or "").strip(),
            "memo_cd": memo_cd,
            "memo_text": ((row[43] if len(row) > 43 else "") or "")[:160],
        })
    return out, f3_11ai


def main() -> None:
    paths = [Path(p) for p in sys.argv[1:]] or sorted(FILINGS.glob("*.csv"))
    roster, by_src = [], {}
    for p in paths:
        rows, f3 = parse(p)
        amt = round(sum(r["amt"] for r in rows), 2)
        by_src[p.stem] = {"n": len(rows), "amt": amt, "form3_line_11ai_period": f3,
                          "gap": round((f3 or 0) - amt, 2)}
        roster.extend(rows)
    summary = {
        "n": len(roster),
        "amt": round(sum(r["amt"] for r in roster), 2),
        "by_src": by_src,
        "form3_itemized": round(sum(v["form3_line_11ai_period"] or 0 for v in by_src.values()), 2),
    }
    summary["gap_vs_form3_itemized"] = round(summary["form3_itemized"] - summary["amt"], 2)
    print(json.dumps(summary, indent=2))
    assert all(v["gap"] == 0 for v in by_src.values()), "a report does not reconcile to its F3 line 11a(i)"
    if sys.argv[1:]:
        return
    with OUT.open("w", encoding="utf-8") as f:
        for r in roster:
            f.write(json.dumps(r, default=str) + "\n")
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
