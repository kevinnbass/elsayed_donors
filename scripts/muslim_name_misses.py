"""Show high-dollar names the classifier left out, for miss review."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "muslim_name_share", ROOT / "scripts" / "muslim_name_share.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

donors = defaultdict(lambda: {"amt": 0.0, "name": ""})
with (ROOT / "analysis" / "roster_named_itemized.jsonl").open(encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        if m.classify(r.get("name") or "") != "no":
            continue
        k = (r.get("last_norm"), r.get("first_norm"))
        donors[k]["amt"] += r["amt"]
        donors[k]["name"] = r.get("name") or ""

ranked = sorted(donors.values(), key=lambda d: -d["amt"])[:40]
print("Top 40 UNMATCHED by $")
for d in ranked:
    print(f"  ${d['amt']:10,.0f}  {d['name']}")
