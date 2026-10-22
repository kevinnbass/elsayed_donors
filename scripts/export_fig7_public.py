"""Export figure 7 (e7-donors-and-groups) and every row behind it, for the public repo.

Usage: ~/.venvs/memes/bin/python scripts/export_fig7_public.py <out_dir>
Writes into <out_dir>: figure/ (png, jpg), data/ (csv and json tables), sources/ (copies of public records: FEC, IRS, court and
U.S. government filings, named by sha256), check_numbers.py, README.md.
Every number is computed with the same functions scripts/mb_figures.py uses to draw the figure. Left out on purpose: street
numbers (only ZIP5 is kept, enough to join to analysis/donors_net.jsonl) and any per-person judgment of a name's heritage
(the figure's name panel is a group total, reproducible from the public lexicon and scripts/name_origin_share.py).
Pages that are not public records (organization sites, press releases, personal pages, foreign-government files) are cited by
URL, sha256 of the saved copy and a short quote, not copied.
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mb_figures as M  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1])
STEM = "e7-donors-and-groups"
EVIDENCE_DIRS = ["/mnt/data/projects/elsayed/mb_evidence", "/mnt/work/elsayed/org_rosters/*/evidence",
                 "/mnt/work/elsayed/terror_records/*/evidence"]
PUBLIC_RECORD_HOSTS = ("projects.propublica.org", "990s.foundationcenter.org", "docquery.fec.gov", "api.open.fec.gov", "fec.gov",
                       "home.treasury.gov", "treasury.gov", "sos.state.tx.us", "flgov.com", "flrules.org", "congress.gov",
                       "govinfo.gov", "cases.justia.com", "investigativeproject.org")
# each sentence of the groups panel and the judged tie (or record) whose primary evidence supports it
STATEMENT_TIES = {"CAIR": [("Named in 2007 on prosecutors' list of unindicted co-conspirators in the Holy Land Foundation "
                            "Hamas-financing case; never charged.", "603ed1d42370"),
                           ("Listed as a terrorist group by the UAE in 2014; labeled one by Texas and Florida in 2025.", "14884feddf61")],
                  "ICNA": [("Named in a 1991 Muslim Brotherhood memo, a Holy Land trial exhibit, on a list headed \"our "
                            "organizations and the organizations of our friends\".", "af45014b141f")],
                  "Islamic Relief USA": [("Its international parent, Islamic Relief Worldwide, was banned by Israel in 2014.", "318714837258")],
                  "MPower Change": [("Published a 2018 report with CAIR.", "f6c6765da9da")],
                  "Unity & Justice Fund": [("Super PAC that CAIR Action helps fund.", "c14954bc49b1")]}

index = {}
for pat in EVIDENCE_DIRS:
    for f in glob.glob(f"{pat}/*"):
        index.setdefault(Path(f).name.split(".")[0], f)


def host(url: str) -> str:
    return (urlsplit(url).hostname or "").removeprefix("www.")


def source_row(url: str, sha: str | None, quote: str | None, kind: str) -> dict:
    copied = ""
    if sha and any(host(url) == h or host(url).endswith("." + h) for h in PUBLIC_RECORD_HOSTS) and sha in index:
        src = index[sha]
        text = open(src, "rb").read()
        if b"api_key" not in text and b"DATA_GOV" not in text:     # never publish a saved request that carries a key
            copied = f"sources/{Path(src).name}"
            (OUT / "sources").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, OUT / copied)
    return {"kind": kind, "url": url, "sha256": sha or "", "quote": (quote or "")[:300], "copy": copied}


def write_csv(name: str, rows: list[dict]) -> None:
    with open(OUT / "data" / name, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


README = """# El-Sayed's donors and the groups in the coverage

![figure](figure/donors-and-groups.png)

One figure about donors to Abdul El-Sayed, the Democratic nominee for U.S. Senate in Michigan in 2026, and every row of data
behind it. Run `python3 check_numbers.py` to recompute each number on the figure from the tables in `data/`.

## What the figure shows

- **Top left.** Of the {n_top} donors who gave El-Sayed's campaign the $7,000 maximum, {pct}% have Arab- or Muslim-heritage
  names (estimate {lo}% to {hi}%; for all donors, {all_pct}%). This measures names, not religion or anyone's ties to any group.
- **Top right.** {people} people with documented roles in CAIR and other Muslim and Arab-advocacy groups gave {total}:
  {campaign} to the campaign and {pacs} to the PACs backing him (Fighting for Michigan, Unity & Justice Fund, MERIT PAC).
  CAIR: {cair_people} people, {cair}, of which {jukaku} is Tayeb Jukaku's gift to Fighting for Michigan.
- **Bottom.** Each group, the people and dollars connected to it, and what public records say about the group.

## How the links were made

A donor counts as staff or a leader of a group when the group's own records name them (IRS Form 990 filings, its website, annual
reports, FEC filings) or when the donor's own FEC filing gives the group as employer, and only when the record and the donor
match on at least two details, such as name and city, or name and employer. Records of one person filed under two addresses
count once. In the ring each person counts once, under CAIR when they also hold a role elsewhere; in the bottom panel a person
with roles in two groups is listed under both.

A role is a documented association with an organization. It says nothing about the person's views or conduct, and the records
about a group describe the organization, not the people connected to it.

## Data

| file | one row per |
|---|---|
| `data/people_roles.csv` | person and documented role ({n_roles} rows): name and city as filed, group, organization and role as recorded, how it was confirmed |
| `data/people_role_sources.csv` | source for a role: URL, sha256 of the saved copy, quote, and the copy in `sources/` when it is a public record |
| `data/people_gifts.csv` | gift behind the money: campaign totals per donor record (net of refunds, through Sep 30, 2026) and each PAC receipt (through Aug 31, 2026) with its FEC file and transaction id |
| `data/ring_by_group.csv` | slice of the ring |
| `data/groups_panel.csv` | group in the bottom panel, with the text shown |
| `data/group_sources.csv` | source for each statement about a group |
| `data/max_donors.csv` | donor who gave the $7,000 maximum (FEC data) |
| `data/name_heritage_totals.json` | the name-heritage totals for those donors and for all donors |
| `data/figure_numbers.json` | every number printed on the figure |

`sources/` holds copies of public records only (FEC, IRS, court and U.S. government filings), named by sha256: {n_copies} files.
Organization pages, press releases, personal pages and foreign-government files are cited by URL, sha256 and quote instead
({n_sources} source rows in all).

**Not included, on purpose:** any per-person judgment of a name's heritage (only totals are published; the lexicon and the
scoring script are public in [kevinnbass/elsayed_donors](https://github.com/kevinnbass/elsayed_donors), `analysis/name_lexicon/`
and `scripts/name_origin_share.py`), and street addresses (ZIP5 is kept so rows can be joined to that repository's
`analysis/donors_net.jsonl`).

## Sources of the money

FEC filings of Abdul for U.S. Senate (itemized gifts from individuals, including those passed through its joint fundraising
committees, net of refunds and reattributions, through Sep 30, 2026) and of Fighting for Michigan PAC, Unity & Justice Fund
and ACMER MERIT PAC (through Aug 31, 2026, as amended through Oct 17, 2026).

## How it was built

`scripts/export_fig7_public.py` in [kevinnbass/elsayed_donors](https://github.com/kevinnbass/elsayed_donors) writes this
repository with the same functions `scripts/mb_figures.py` uses to draw the figure.
"""


def main() -> None:
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    (OUT / "figure").mkdir(parents=True, exist_ok=True)
    for ext in ("png", "jpg"):
        shutil.copyfile(ROOT / "analysis" / "private" / "figures" / f"{STEM}.{ext}", OUT / "figure" / f"donors-and-groups.{ext}")

    CAIR = "CAIR (national and chapters)"
    fam_of = lambda orgs: {next(n for pat, n, _ in M.FAMILY if re.search(pat, o)) for o, _ in orgs}
    people = M.role_people(M.PAC_END)
    folks = sorted([p for p in M.persons(people) if p["campaign"] or p["pac"]], key=lambda p: (p["name"].upper(), p["keys"][0]))
    pid = {}
    for i, p in enumerate(folks, 1):
        p["id"] = f"P{i:02d}"
        for k in p["keys"]:
            pid[k] = p["id"]
    short = lambda f: M.GROUP_TEXT[f][0]

    # people and their roles, one row per record and role, with every source
    roles, sources = [], []
    for r in M.load("donor_org_roles_confirmed"):
        key = (" ".join(r["donor"].upper().split()), r["city"].upper(), r["state"])
        fam = next((n for pat, n, _ in M.FAMILY if re.search(pat, r["org"])), None)
        if key not in pid or not fam:
            continue
        roles.append({"person_id": pid[key], "name_as_filed": r["donor"], "city": r["city"], "state": r["state"], "group": short(fam),
                      "organization_as_recorded": r["org"], "role_as_recorded": r["roles"], "how_confirmed": r["basis"]})
        for e in r["evidence"]:
            if not isinstance(e, dict):
                continue
            if e.get("url"):
                sources.append({"person_id": pid[key], "group": short(fam),
                                **source_row(e["url"], e.get("sha256"), e.get("quote"), "role record")})
            elif e.get("source"):
                sources.append({"person_id": pid[key], "group": short(fam), "kind": "donor's own FEC filing (employer field)",
                                "url": e["source"][:300], "sha256": "", "quote": "", "copy": ""})
    # gifts: campaign totals per donor record (net of refunds) and each PAC receipt
    gifts = []
    for p in folks:
        for d in p["campaign"]:
            gifts.append({"person_id": p["id"], "committee": "Abdul for U.S. Senate", "kind": "campaign, net of refunds through 2026-09-30",
                          "date": "", "amount": round(d["net"], 2), "name_as_filed": d["name"], "city": d["city"], "state": d["state"],
                          "zip5": d["zip5"], "fec_file_number": "", "transaction_id": "", "n_gifts": d["n_gifts"], "gross": d["gross"]})
        for r in p["pac"]:
            gifts.append({"person_id": p["id"], "committee": r["committee"], "kind": "PAC receipt", "date": r["date"], "amount": r["amount"],
                          "name_as_filed": r["contributor"], "city": r["city"], "state": r["state"], "zip5": "",
                          "fec_file_number": r["file_number"], "transaction_id": r["transaction_id"], "n_gifts": 1, "gross": r["amount"]})
    # the ring: each person once, under CAIR when they also hold a role elsewhere
    ring = defaultdict(list)
    for p in folks:
        fams = fam_of(p["orgs"])
        ring[CAIR if CAIR in fams else sorted(fams)[0]].append(p)
    camp = lambda grp: round(sum(d["net"] for p in grp for d in p["campaign"]), 2)
    pacs = lambda grp: round(sum(r["amount"] or 0 for p in grp for r in p["pac"]), 2)
    ring_rows = [{"group": short(g), "people": len(ps), "campaign": camp(ps), "pacs": pacs(ps), "total": round(camp(ps) + pacs(ps), 2)}
                 for g, ps in sorted(ring.items(), key=lambda x: -(camp(x[1]) + pacs(x[1])))]
    panel = defaultdict(list)
    for p in folks:
        for f in fam_of(p["orgs"]):
            panel[f].append(p)
    panel_rows = [{"group": short(f), "people": len(ps), "campaign": camp(ps), "pacs": pacs(ps), "description_on_figure": M.GROUP_TEXT[f][1]}
                  for f, ps in sorted(panel.items(), key=lambda x: (x[0] != CAIR, -(camp(x[1]) + pacs(x[1]))))]
    # sources for the group descriptions
    verdicts = {json.loads(l)["tie_id"]: json.loads(l) for l in open(ROOT / "analysis" / "private" / "mb_verdicts.jsonl", encoding="utf-8")}
    group_sources = []
    for g, items in STATEMENT_TIES.items():
        for statement, tid in items:
            v = verdicts[tid]
            for e in v.get("primary_evidence") or []:
                sha = (e.get("file") or "").split(".")[0] or None
                group_sources.append({"group": g, "statement": statement,
                                      **source_row(e.get("url", ""), sha, e.get("quote"), e.get("kind", ""))})
    kh = [r for r in map(json.loads, open(ROOT / "analysis" / "private" / "terror_records" / "records.jsonl", encoding="utf-8"))
          if re.search("Kind ?Hearts", r.get("case_or_action") or "", re.I)][:1]
    for r in kh:
        group_sources.append({"group": "KindHearts", "statement": "Treasury froze its assets in 2006 \"pending investigation\", calling it "
                              "tied to Hamas; it was never formally designated.",
                              **source_row(r["source_url"], r["sha256"], "Treasury Freezes Assets of Organization Tied to Hamas ... blocked "
                                           "pending investigation accounts of KindHearts", "government")})
    # the 644 donors at the limit (public FEC data) and the name-heritage totals for them
    top = [d for d in map(json.loads, open(ROOT / "analysis" / "donors_net.jsonl", encoding="utf-8")) if d["net"] >= M.LIMIT - 0.005]
    max_rows = [{"name_as_filed": d["name"], "city": d["city"], "state": d["state"], "zip5": d["zip5"], "net": d["net"], "gross": d["gross"],
                 "n_gifts": d["n_gifts"]} for d in sorted(top, key=lambda d: (d["name"].upper(), d["zip5"]))]
    share = json.loads((ROOT / "analysis" / "name_origin_share.json").read_text(encoding="utf-8"))
    heritage = {"donors_at_the_limit": share["by_donor_tier"]["at_7000_max"], "all_donors": share["by_donor_tier"]["all_donors"],
                "method": share["method"], "how": "Each donor's name is scored with a name-origin lexicon (analysis/name_lexicon in "
                "kevinnbass/elsayed_donors) by scripts/name_origin_share.py there; the shares are sums over donors. Only group totals "
                "are published."}
    total = camp(folks) + pacs(folks)
    numbers = {"total_to_campaign_and_pacs": round(total, 2), "people": len(folks), "campaign": camp(folks), "pacs": pacs(folks),
               "donors_at_the_limit": len(top), "heritage_share_pct_shown": round(heritage["donors_at_the_limit"]["expected_pct_of_donors"]),
               "heritage_dollar_share_pct_shown": round(heritage["donors_at_the_limit"]["expected_pct_of_net_dollars"]),
               "ring": ring_rows}
    write_csv("people_roles.csv", roles)
    write_csv("people_role_sources.csv", sources)
    write_csv("people_gifts.csv", gifts)
    write_csv("ring_by_group.csv", ring_rows)
    write_csv("groups_panel.csv", panel_rows)
    write_csv("group_sources.csv", group_sources)
    write_csv("max_donors.csv", max_rows)
    (OUT / "data" / "name_heritage_totals.json").write_text(json.dumps(heritage, indent=1), encoding="utf-8")
    (OUT / "data" / "figure_numbers.json").write_text(json.dumps(numbers, indent=1), encoding="utf-8")
    shutil.copyfile(Path(__file__).with_name("fig7_check_numbers.py"), OUT / "check_numbers.py")
    (OUT / "README.md").write_text(README.format(
        total=M.money(total), people=len(folks), campaign=M.money(camp(folks)), pacs=M.money(pacs(folks)),
        cair_people=next(r["people"] for r in ring_rows if r["group"] == "CAIR"), cair=M.money(next(r["total"] for r in ring_rows if r["group"] == "CAIR")),
        jukaku=M.money(max(sum(r["amount"] or 0 for r in p["pac"]) for p in folks)), n_top=len(top),
        pct=numbers["heritage_share_pct_shown"], lo=heritage["donors_at_the_limit"]["low_pct_of_donors"],
        hi=heritage["donors_at_the_limit"]["high_pct_of_donors"], all_pct=heritage["all_donors"]["expected_pct_of_donors"],
        n_roles=len(roles), n_sources=len(sources) + len(group_sources),
        n_copies=len({s["copy"] for s in sources + group_sources if s["copy"]})), encoding="utf-8")
    print(json.dumps({k: v for k, v in numbers.items() if k != "ring"}), f"| roles {len(roles)} | role sources {len(sources)} "
          f"(copied {sum(1 for s in sources if s['copy'])}) | gifts {len(gifts)} | group sources {len(group_sources)} "
          f"(copied {sum(1 for s in group_sources if s['copy'])}) | max donors {len(max_rows)}")


if __name__ == "__main__":
    main()
