"""Figure audit for the claims-database figures (gate G5 of the anthropic verification gold standard, adapted):
every drawn element resolves to row ids that exist in the tables; the hidden `<!-- rows: -->` comment resolves; no row id
is printed in visible text; scripts/mb_figures.py carries no amount literal (dollar strings or integers of 5,000 or more,
other than lines marked `# parameter`).

Usage: python scripts/mb_audit_figures.py [stem ...]     exit 0 = PASS (all figures when no stem is given)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "analysis" / "private" / "mb_claims"
FIGS = ROOT / "analysis" / "private" / "figures"
PY = str(Path.home() / ".venvs/memes/bin/python")
CODE = {"Fighting for Michigan PAC": "FFM", "Unity & Justice Fund": "UJF", "American Priorities": "AMP", "ACMER MERIT PAC": "MRT"}
load = lambda n: [json.loads(l) for l in open(DATA / f"{n}.jsonl", encoding="utf-8")]

known = {f"T{t['tie_id']}" for t in load("ties")} | {f"C{c['claim_id']}" for c in load("claims")}
known |= {f"R:{CODE[r['committee']]}:{r['transaction_id']}" for r in load("super_pac_receipts")}
known |= {f"R:{CODE[r['committee']]}:{r['transaction_id']}" for r in load("fec_rows") if r["committee"] in CODE}
known |= {f"F:{r['fec_file_number']}:{r['transaction_id']}" for r in load("fec_rows") if r["committee"] not in CODE}
ID = re.compile(r"\b(?:T[0-9a-f]{12}|C[0-9a-f]{16}-\d+|R:[A-Z]{3}:\S+|F:\d+:\S+|[0-9a-f]{12,16})\b")

problems = []
code = (ROOT / "scripts" / "mb_figures.py").read_text(encoding="utf-8").splitlines()
for i, line in enumerate(code, 1):
    if "# parameter" in line or line.lstrip().startswith("#"):
        continue
    stripped = re.sub(r"\{[^}]*\}", "", line)           # f-string fields are computed, not literals
    if re.search(r"\$\s?\d", stripped) or re.search(r"\b\d{1,3},\d{3}\b", stripped) or any(int(n) >= 5000 for n in re.findall(r"\b\d{4,}\b", stripped)):
        problems.append(f"mb_figures.py line {i}: amount-like literal: {line.strip()[:100]}")

listed = subprocess.run([PY, str(ROOT / "scripts" / "mb_figures.py"), "--list-elements"], capture_output=True, text=True)
elements = json.loads(listed.stdout[listed.stdout.index("["):]) if "[" in listed.stdout else []
if not elements:
    problems.append("mb_figures.py --list-elements returned nothing: " + listed.stderr[-300:])
for e in elements:
    if not e["rows"]:
        problems.append(f"element without a row id: {e['kind']} {e['from']}")
    problems += [f"element row not in tables: {r} ({e['kind']} {e['from']})" for r in e["rows"] if r not in known]

stems = sys.argv[1:] or sorted(p.stem for p in FIGS.glob("*.html"))
for stem in stems:
    html = (FIGS / f"{stem}.html").read_text(encoding="utf-8")
    m = re.search(r"<!-- rows: (.*?) -->", html, re.S)
    cited = set(m.group(1).split()) if m else set()
    if not cited:
        problems.append(f"{stem}: no hidden rows comment")
    problems += [f"{stem}: cited id not in tables: {i}" for i in sorted(cited - known)]
    visible = re.sub(r"<[^>]+>", " ", re.sub(r"<!--.*?-->", "", html, flags=re.S))
    problems += [f"{stem}: id-like token printed on the figure: {t}" for t in sorted(set(ID.findall(visible)))]
    for ext in ("png", "jpg"):
        if not (FIGS / f"{stem}.{ext}").exists():
            problems.append(f"{stem}: missing {ext}")
for p in problems:
    print(p)
print(f"AUDIT {'PASS' if not problems else 'FAIL'}: {len(stems)} figures, {len(elements)} elements, {len(problems)} problems")
sys.exit(1 if problems else 0)
