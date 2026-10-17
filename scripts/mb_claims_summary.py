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
# super PAC contributors of $50,000 or more whom no captured story names (by adjacent first + last name, or org name)
rec = load("super_pac_receipts")
agg = defaultdict(lambda: {"amount": 0.0, "n_stories": 0, "rows": 0})
for r in rec:
    k = (r["committee"], " ".join(r["contributor"].upper().split()), r["entity_type"])
    a = agg[k]
    a["amount"] += r["amount"] or 0
    a["rows"] += 1
    a["n_stories"] = max(a["n_stories"], r["n_stories_naming_contributor"])
    a.update({"city": r["city"], "state": r["state"], "occupation": r["occupation"], "employer": r["employer"]})
unnamed = [{"committee": k[0], "contributor": k[1], "entity_type": k[2], **v} for k, v in agg.items()
           if v["amount"] >= 50000 and v["n_stories"] == 0]
unnamed.sort(key=lambda u: (u["committee"], -u["amount"]))
with (OUT / "super_pac_donors_unnamed_in_stories.jsonl").open("w", encoding="utf-8") as f:
    for u in unnamed:
        f.write(json.dumps(u, ensure_ascii=False) + "\n")
lines += ["", "## Super PAC contributors of $50,000+ named in no captured story", "",
          "Name search is a screen (adjacent first and last name, or the organization's name), not proof of absence: a donor "
          "reported under another name form (e.g. a nickname) appears here too. Not every American Priorities donor gave "
          "for El-Sayed's race; the PAC is listed because stories tie its spending to him.", "",
          "| committee | contributor | city | occupation / employer | total |", "|---|---|---|---|---|"]
lines += [f"| {u['committee']} | {u['contributor']} | {u['city']}, {u['state']} | {u['occupation']} / {u['employer']} | ${u['amount']:,.0f} |"
          for u in unnamed]
(OUT / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {OUT / 'SUMMARY.md'}: {len(ties)} ties")
