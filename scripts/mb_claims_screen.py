"""Keyword screen of captured articles: which go to claim extraction, and why the rest do not.

Usage: python scripts/mb_claims_screen.py <mb_claims_dir>
Reads <mb_claims_dir>/raw_dl/<h>.{json,txt}; writes <mb_claims_dir>/screen.jsonl (one row per captured article)
and lists the hashes that pass and are not yet extracted in <mb_claims_dir>/extract_todo_new.txt.
An article passes when its text names El-Sayed and at least one theme keyword. The screen is deliberately
loose; the extraction step decides scope from the full text. Person-name keywords are read from
analysis/private/mb_screen_names.txt (gitignored) so the public script names no one.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

MB = Path(sys.argv[1])
ROOT = Path(__file__).resolve().parents[1]
ELS = re.compile(r"el[- ]?sayed|elsayed|abdulrahman el", re.I)
THEMES = (r"brotherhood|\bCAIR\b|Council on American-Islamic|\bISNA\b|Islamic Society of North America|\bIARA\b|"
          r"Islamic American Relief|Holy Land|Hamas|Hezbollah|ACMER|Middle East Rights|Life for Relief|\bAMP\b|"
          r"American Muslims for Palestine|AJP Action|Islamist|terror|Fighting for Michigan|Unity (&|and) Justice|Ikhwan|"
          r"fatwa|MEMRI|jihad|sharia|Morsi|Qatar|Khamenei")
# names of people the coverage is about stay out of the public script: one regex alternative per line, if present
NAMES = ROOT / "analysis" / "private" / "mb_screen_names.txt"
extra = [l.strip() for l in NAMES.open(encoding="utf-8") if l.strip()] if NAMES.exists() else []
KW = re.compile("|".join([THEMES, *extra]), re.I)

done = set()
for f in glob.glob(str(MB / "extract_v2" / "*" / "claims.jsonl")) + glob.glob(str(MB / "extract_v3" / "*" / "claims.jsonl")):
    done |= {json.loads(l)["h"] for l in open(f, encoding="utf-8") if l.strip()}
rows, todo = [], []
for jp in sorted(glob.glob(str(MB / "raw_dl" / "*.json"))):
    h = Path(jp).stem
    m = json.load(open(jp))
    if m.get("status") != "ok":
        rows.append({"h": h, "screen": "not_captured", "status": m.get("status")})
        continue
    t = (MB / "raw_dl" / f"{h}.txt").read_text(errors="replace")
    kws = sorted({m_.group(0).lower() for m_ in KW.finditer(t)})
    if not ELS.search(t):
        res = "out_no_el_sayed"
    elif not kws:
        res = "out_no_theme_keyword"
    else:
        res = "extracted" if h in done else "to_extract"
        if h not in done:
            todo.append(h)
    rows.append({"h": h, "screen": res, "keywords": kws[:12]})
with open(MB / "screen.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
(MB / "extract_todo_new.txt").write_text("".join(h + "\n" for h in todo))
counts = {}
for r in rows:
    counts[r["screen"]] = counts.get(r["screen"], 0) + 1
print(counts, "| new to extract:", len(todo))
