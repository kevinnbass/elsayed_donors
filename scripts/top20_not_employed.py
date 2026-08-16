"""Top 20 named donors whose occupation is not-employed / retired / homemaker."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "analysis" / "roster_named_itemized.jsonl"
OUT = ROOT / "analysis" / "top20_not_employed.json"

PAT = re.compile(
    r"NOT EMPLOYED|UNEMPLOYED|RETIRED|HOMEMAKER|DISABLED|"
    r"^NONE$|^N/?A$|^NA$",
    re.I,
)

# don't treat blank as this bucket
def in_bucket(occ: str) -> bool:
    o = (occ or "").strip()
    if not o:
        return False
    return bool(PAT.search(o))


def main() -> None:
    donors = defaultdict(lambda: {"amt": 0.0, "n": 0, "name": "", "occs": set()})
    tot = 0.0
    with ROSTER.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            occ = r.get("occupation") or ""
            if not in_bucket(occ):
                continue
            tot += r["amt"]
            k = (r.get("last_norm") or "", r.get("first_norm") or "", (r.get("name") or "").upper())
            d = donors[k]
            d["amt"] += r["amt"]
            d["n"] += 1
            d["name"] = r.get("name") or ""
            d["occs"].add(occ.strip())

    ranked = sorted(donors.values(), key=lambda d: -d["amt"])[:20]
    out = {
        "bucket_amt": round(tot, 2),
        "n_names_in_bucket": len(donors),
        "top20": [
            {
                "rank": i + 1,
                "name": d["name"],
                "amt": round(d["amt"], 2),
                "n_gifts": d["n"],
                "occupation": sorted(d["occs"], key=lambda x: -len(x))[0],
            }
            for i, d in enumerate(ranked)
        ],
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"bucket ${tot:,.2f}  distinct names {len(donors)}\n")
    for r in out["top20"]:
        print(f"{r['name']} — ${r['amt']:,.0f} — {r['occupation']}")


if __name__ == "__main__":
    main()
