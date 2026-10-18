"""Recompute every number on the figure from the tables in data/ and compare with data/figure_numbers.json.

Usage: python3 check_numbers.py        (exit 0 = every number matches)
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

D = Path(__file__).resolve().parent / "data"
rows = lambda name: list(csv.DictReader(open(D / name, encoding="utf-8")))
shown = json.loads((D / "figure_numbers.json").read_text(encoding="utf-8"))
problems = []


def same(label, got, want):
    ok = abs(float(got) - float(want)) < 0.01
    print(f"{'ok ' if ok else 'BAD'} {label}: {got:,.2f} (figure {float(want):,.2f})" if isinstance(got, float) else
          f"{'ok ' if ok else 'BAD'} {label}: {got} (figure {want})")
    if not ok:
        problems.append(label)


gifts = rows("people_gifts.csv")
people = {g["person_id"] for g in gifts}
campaign = sum(float(g["amount"]) for g in gifts if g["committee"] == "Abdul for U.S. Senate")
pacs = sum(float(g["amount"]) for g in gifts if g["committee"] != "Abdul for U.S. Senate")
same("people with roles who gave", len(people), shown["people"])
same("to the campaign", campaign, shown["campaign"])
same("to PACs", pacs, shown["pacs"])
same("total (the ring)", campaign + pacs, shown["total_to_campaign_and_pacs"])

# the ring: each person once, under CAIR when they also hold a role elsewhere
groups = defaultdict(set)
for r in rows("people_roles.csv"):
    groups[r["person_id"]].add(r["group"])
by_person = defaultdict(float)
for g in gifts:
    by_person[g["person_id"]] += float(g["amount"])
ring = defaultdict(lambda: [0, 0.0])
for p, gs in groups.items():
    if p not in by_person:
        continue
    g = "CAIR" if "CAIR" in gs else sorted(gs)[0]
    ring[g][0] += 1
    ring[g][1] += by_person[p]
for r in shown["ring"]:
    same(f"ring {r['group']} people", ring[r["group"]][0], r["people"])
    same(f"ring {r['group']} dollars", ring[r["group"]][1], r["total"])

top = rows("max_donors.csv")
same("donors at the $7,000 limit", len(top), shown["donors_at_the_limit"])
h = json.loads((D / "name_heritage_totals.json").read_text(encoding="utf-8"))["donors_at_the_limit"]
same("share with Arab- or Muslim-heritage names (rounded)", round(h["expected_pct_of_donors"]), shown["heritage_share_pct_shown"])
same("their share of the group's dollars (rounded)", round(h["expected_pct_of_net_dollars"]), shown["heritage_dollar_share_pct_shown"])
print("ALL NUMBERS MATCH" if not problems else f"{len(problems)} MISMATCHES")
raise SystemExit(1 if problems else 0)
