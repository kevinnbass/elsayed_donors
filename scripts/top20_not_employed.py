"""Not-employed / retired / homemaker donors at the $7,000 maximum, on net totals.

Bucket dollars are gift-level (occupation as filed on each gift). A donor is in the bucket
when the occupation carrying most of their dollars is (analysis/donors_net.jsonl, from
scripts/top_donors.py). Students are left out, as before.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "analysis" / "roster_named_itemized.jsonl"
DONORS = ROOT / "analysis" / "donors_net.jsonl"
OUT = ROOT / "analysis" / "top20_not_employed.json"
TXT = ROOT / "analysis" / "TOP20_not_employed.txt"
CAP = 7000.0

PAT = re.compile(
    r"NOT[ -]EMPLOYED|UNEMPLOYED|RETIRED|HOME ?MAKER|STAY AT HOME|DISABLED|"
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
    tot = 0.0
    with ROSTER.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if in_bucket(r.get("occupation") or ""):
                tot += r["amt"]

    donors = [json.loads(line) for line in DONORS.open(encoding="utf-8")]
    bucket = [d for d in donors if in_bucket(d["occupation"])]
    at_cap = sorted([d for d in bucket if d["net"] >= CAP - 0.005], key=lambda d: (-d["net"], d["name"]))
    out = {
        "basis": "net of refunds and reattributions (scripts/top_donors.py)",
        "bucket_amt": round(tot, 2),
        "n_donors_in_bucket": len(bucket),
        "bucket_net": round(sum(d["net"] for d in bucket), 2),
        "n_at_cap": len(at_cap),
        "at_cap": [
            {"name": d["name"], "state": d["state"], "net": d["net"], "n_gifts": d["n_gifts"],
             "occupation": d["occupation"]}
            for d in at_cap
        ],
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

    lines = [
        "Not-employed / retired / homemaker donors at the $7,000 maximum (net of refunds and reattributions)",
        f"Named itemized $ in this bucket: ${tot / 1e6:.2f}M ({len(bucket):,} donors). Occupation as filed.",
        f"{len(at_cap)} gave the maximum, so a top 20 would be an arbitrary cut; all are listed.",
        "",
    ]
    lines += [f"{d['name']} — ${d['net']:,.0f} — {d['occupation']}" for d in at_cap]
    text = "\n".join(lines) + "\n"
    TXT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
