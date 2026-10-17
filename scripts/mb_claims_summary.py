"""Summarize the claims database: coverage, verdicts, and the most-repeated ties with their verdicts.

Usage: python scripts/mb_claims_summary.py <out_dir>   (the folder mb_claims_build.py wrote)
Writes <out_dir>/SUMMARY.md. Reads only the built tables.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(sys.argv[1])
load = lambda n: [json.loads(l) for l in open(OUT / f"{n}.jsonl", encoding="utf-8")]
stories, claims, links, ents, ties = load("stories"), load("claims"), load("links"), load("entities"), load("ties")
ORDER = ["holds_up", "holds_up_partly", "contradicted", "about_someone_else", "unsupported",
         "statement_verified", "statement_not_verified", None]

lines = ["# Claims database summary", ""]
disp = Counter(s["disposition"] for s in stories)
lines += [f"Stories captured: {len(stories)}. "
          + "; ".join(f"{k} {v}" for k, v in sorted(disp.items())), "",
          f"Claims: {len(claims)}. Links: {len(links)} ({sum(1 for l in links if l['cited_for_a_claim'])} cited for a claim). "
          f"Entities: {len(ents)}. Distinct ties: {len(ties)}, with verdicts {sum(1 for t in ties if t['verdict'])}.", ""]

lines += ["## Verdicts by kind of subject", "", "| subject kind | " + " | ".join(str(o) for o in ORDER) + " |",
          "|---|" + "---|" * len(ORDER)]
by = defaultdict(Counter)
for t in ties:
    by[t["kind"]][t["verdict"]] += 1
for k, c in sorted(by.items(), key=lambda kv: -sum(kv[1].values())):
    lines.append(f"| {k} | " + " | ".join(str(c.get(o, 0)) for o in ORDER) + " |")

lines += ["", "## Ties repeated in the most stories", "",
          "| entity | link | counterparty / recipient | stories | outlets | stated | FEC | verdict | why |", "|---|---|---|---|---|---|---|---|---|"]
for t in sorted(ties, key=lambda t: -t["n_stories"])[:60]:
    why = (t.get("adjudication") or t.get("verdict_reason") or "").replace("|", "/").replace("\n", " ")
    fec = f"${t['fec_amount']:,.0f}" if isinstance(t.get("fec_amount"), (int, float)) else ""
    lines.append(f"| {t['entity']} | {t['link_type']} | {t['counterparty_or_recipient']} | {t['n_stories']} | {t['n_outlets']} | "
                 f"{t['amounts_stated']} | {fec} | {t['verdict'] or 'pending'} | {why[:300]} |")

lines += ["", "## Every contradicted or about-someone-else tie", ""]
for t in ties:
    if t["verdict"] in ("contradicted", "about_someone_else"):
        lines.append(f"- **{t['entity']}**, {t['link_type']} {t['counterparty_or_recipient']} ({t['n_stories']} stories): "
                     f"{t['verdict']}. {(t.get('adjudication') or t.get('verdict_reason') or '').strip()}")
(OUT / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {OUT / 'SUMMARY.md'}: {len(ties)} ties")
