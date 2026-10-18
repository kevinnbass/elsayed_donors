"""Figures for the published-claims database, drawn on the evaluators-deep surface (scripts/fig_common.py).

Usage: ~/.venvs/memes/bin/python scripts/mb_figures.py [stem ...]      render (all figures when no stem is given)
       ~/.venvs/memes/bin/python scripts/mb_figures.py --list-elements  every drawn element with its row ids (JSON)
Reads the built tables in analysis/private/mb_claims/ and writes analysis/private/figures/<stem>.{html,png,jpg}.
Every number on a figure comes from those tables; row ids ride in a hidden comment (T = tie, C = claim, R = super PAC
receipt, F = campaign filing row) and are never printed. Thresholds are parameters (lines marked `# parameter`).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fig_common import (AQUA, AXIS, BG, BLUE, BLUE250, GRAY, GRID, INK, LGRAY, MUTED, ORANGE, PURPLE, RED, YELLOW, cite, esc,  # noqa: E402
                        legend, money, render, shell)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "analysis" / "private" / "mb_claims"
load = lambda n: [json.loads(l) for l in open(DATA / f"{n}.jsonl", encoding="utf-8")]
W = 2400
ELEMENTS: list[dict] = []
COMMITTEE_CODE = {"Fighting for Michigan PAC": "FFM", "Unity & Justice Fund": "UJF", "American Priorities": "AMP",
                  "ACMER MERIT PAC": "MRT"}


def element(kind: str, label: str, rows: list[str]) -> list[str]:
    ELEMENTS.append({"kind": kind, "from": label, "to": "", "rows": sorted(set(rows))})
    return rows


def receipt_id(r: dict) -> str:
    return f"R:{COMMITTEE_CODE[r['committee']]}:{r['transaction_id']}"


def donor_id(d: dict) -> str:
    """A campaign donor (donors_net key); spaces become underscores so the id survives the space-separated rows comment."""
    return f"D:{d['last_norm']}|{d['first_norm']}|{d['suffix']}|{d['zip5']}|{d['house']}".replace(" ", "_")


ACRONYMS = {"PAC", "LLC", "UAW", "IMEU", "CAIR", "MI", "DC", "USA", "US", "II", "III", "V", "CAP", "INC", "ACMER"}
SMAP = json.loads((ROOT / "analysis" / "private" / "mb_subject_map.json").read_text(encoding="utf-8"))
ALIAS = {tuple(v.split("|")): k for k, v in SMAP["fec_aliases"].items()}   # (LAST, FIRST) as filed -> name as articles write it


def titled(words: list[str]) -> str:
    small = {"for", "of", "and", "the", "to", "in"}
    out = []
    for i, w in enumerate(words):
        core = re.sub(r"[^A-Za-z]", "", w).upper()
        out.append(w.upper() if core in ACRONYMS else w.lower() if (i and w.lower() in small) else w.capitalize())
    return " ".join(out)


def person(name: str) -> str:
    """'LIU, ALLEN' -> 'Allen Liu' (or the article form when the FEC record reverses a known name)."""
    name = re.sub(r"\s+", " ", name.strip().rstrip(","))
    last, _, first = name.partition(",")
    key = (re.sub(r"[^A-Z]", "", last.upper()), re.sub(r"[^A-Z]", "", (first.split() or [""])[0].upper()))
    if key in ALIAS:
        return ALIAS[key]
    return titled(f"{first.strip()} {last.strip()}".split())


def short_org(name: str) -> str:
    name = re.sub(r"\s+", " ", name.strip().rstrip(","))
    m = re.match(r"^(?:THE )?.*\(([A-Z]{2,6})\)\s*(.+)$", name, re.I)
    if m and m.group(2).strip():                      # "... (IMEU) POLICY PROJECT" -> "IMEU Policy Project"
        return m.group(1).upper() + " " + titled(m.group(2).split())
    name = re.sub(r"\s*\(.*$", "", name)               # drop a long parenthetical and what follows (UAW's union name)
    words = name.split()
    return (titled(words) if name.isupper() else name)[:60]


# ---- figure 1: money from Muslim and Arab-advocacy organizations and from people holding roles in them ------------------
# organization families for the role table (as the roster lanes named them) and the organizations' own gifts
FAMILY = [(r"^CAIR|Council on American", "CAIR (national and chapters)", "muslim"), (r"ICNA", "ICNA and ICNA Relief", "muslim"),
          (r"Islamic Relief", "Islamic Relief USA", "muslim"), (r"Emgage", "Emgage", "muslim"), (r"MPower", "MPower Change", "muslim"),
          (r"USCMO", "U.S. Council of Muslim Organizations", "muslim"), (r"KindHearts", "KindHearts (closed 2006)", "muslim"),
          (r"Unity & Justice", "Unity & Justice Fund (super PAC CAIR Action helps fund)", "muslim"),
          (r"IMEU", "IMEU", "arab"), (r"ACMER", "ACMER and its MERIT PAC", "arab"), (r"AAPAC|Arab American Political", "Arab American PAC", "arab")]
ORG_GIFTS = [(r"^CAIR ACTION", "CAIR Action", "muslim"), (r"^UNITY & JUSTICE FUND", "Unity & Justice Fund", "muslim"),
             (r"MIDDLE EAST UNDERSTANDING", "IMEU (as amended: IMEU Policy Project)", "arab"),
             (r"COMMITTEE FOR MIDDLE EAST RIGHTS", "ACMER", "arab")]


def fig_islam_money() -> tuple[str, int]:
    roles = load("donor_org_roles_confirmed")
    donors = [json.loads(l) for l in open(ROOT / "analysis" / "donors_net.jsonl", encoding="utf-8")]
    by_nc = defaultdict(list)
    for d in donors:
        by_nc[(" ".join(d["name"].upper().split()), d["city"].upper(), d["state"])].append(d)
    recs = [r for r in load("super_pac_receipts") if r["committee"] in ("Fighting for Michigan PAC", "Unity & Justice Fund", "ACMER MERIT PAC")]
    rec_by_nc = defaultdict(list)
    for r in recs:
        if r["entity_type"] == "IND":
            rec_by_nc[(" ".join(r["contributor"].upper().replace(",", ", ").split()).replace(" ,", ","), (r["city"] or "").upper())].append(r)
    # named in stories: by name in the text, or matched by the claims tables (misspellings, name order) to a story's subject
    claimed = {(" ".join(r["name_as_filed"].upper().split()), (r["city"] or "").upper()) for r in load("fec_rows")
               if r["committee"] == "Abdul for U.S. Senate"}
    fam = {}
    people = {}
    for r in roles:
        f = next(((name, kind) for pat, name, kind in FAMILY if re.search(pat, r["org"])), None)
        if not f:
            continue
        key = (" ".join(r["donor"].upper().split()), r["city"].upper(), r["state"])
        if key not in people:
            camp = by_nc.get(key, [])
            pacs = rec_by_nc.get((" ".join(r["donor"].upper().replace(",", ", ").split()).replace(" ,", ","), r["city"].upper()), [])
            people[key] = {"amount": sum(d["net"] for d in camp) + sum(p["amount"] or 0 for p in pacs),
                           "named": r["n_stories_naming_donor"] > 0 or (key[0], key[1]) in claimed, "name": r["donor"],
                           "rows": [donor_id(d) for d in camp]
                                   + [receipt_id(p) for p in pacs]}
        fam.setdefault(f, set()).add(key)
    org_rows = []
    for pat, label, kind in ORG_GIFTS:
        rs = [r for r in recs if r["entity_type"] != "IND" and re.search(pat, r["contributor"].upper())
              and not r["contributor"].upper().startswith(r["committee"].upper())]      # not a committee's own transfers
        if rs:
            to = sorted({r["committee"] for r in rs})
            org_rows.append((label, kind, sum(r["amount"] or 0 for r in rs), to, [receipt_id(r) for r in rs]))
    fam_rows = sorted(((name, kind, keys) for (name, kind), keys in fam.items()), key=lambda x: (x[1] != "muslim", -sum(people[k]["amount"] for k in x[2])))
    top = max([o[2] for o in org_rows] + [sum(people[k]["amount"] for k in keys) for _, _, keys in fam_rows])
    row_h, label_w, x_bar = 58, 640, 660
    bar_w = W - 120 - x_bar - 420
    h_svg = 60 + (len(org_rows) + len(fam_rows)) * row_h + 130
    svg, ids, y = [f'<svg width="{W - 120}" height="{h_svg}" viewBox="0 0 {W - 120} {h_svg}">'], [], 40
    svg.append(f'<text x="0" y="{y}" font-size="24" font-weight="bold" fill="{INK}">Organizations, gifts of their own</text>')
    y += 24
    for label, kind, amt, to, rows in org_rows:
        w = bar_w * amt / top
        dest = " and ".join("FFM" if t.startswith("Fighting") else "U&J" if t.startswith("Unity") else "MERIT" for t in to)
        svg.append(f'<text x="0" y="{y + 30}" font-size="19" fill="{INK}">{esc(label)}</text>'
                   f'<rect x="{x_bar}" y="{y + 10}" width="{w:.1f}" height="30" rx="3" fill="{BLUE if kind == "muslim" else PURPLE}"/>'
                   f'<text x="{x_bar + w + 10:.1f}" y="{y + 32}" font-size="18" font-weight="bold" fill="{INK}">{money(amt)} to {esc(dest)}</text>')
        ids += element("org bar", label, rows)
        y += row_h
    y += 36
    svg.append(f'<text x="0" y="{y}" font-size="24" font-weight="bold" fill="{INK}">People with documented roles, by organization (campaign and super PAC gifts)</text>')
    y += 24
    for name, kind, keys in fam_rows:
        named = [k for k in keys if people[k]["named"]]
        unnamed = [k for k in keys if not people[k]["named"]]
        a_n, a_u = sum(people[k]["amount"] for k in named), sum(people[k]["amount"] for k in unnamed)
        w_n, w_u = bar_w * a_n / top, bar_w * a_u / top
        svg.append(f'<text x="0" y="{y + 30}" font-size="19" fill="{INK}">{esc(name)}</text>'
                   f'<rect x="{x_bar}" y="{y + 10}" width="{w_n:.1f}" height="30" fill="{BLUE if kind == "muslim" else PURPLE}"/>'
                   f'<rect x="{x_bar + w_n:.1f}" y="{y + 10}" width="{w_u:.1f}" height="30" fill="{ORANGE}"/>'
                   f'<text x="{x_bar + w_n + w_u + 10:.1f}" y="{y + 32}" font-size="18" font-weight="bold" fill="{INK}">{money(a_n + a_u)}</text>'
                   f'<text x="{W - 120}" y="{y + 32}" font-size="17" fill="{MUTED}" text-anchor="end">'
                   f'{len(keys)} {"person" if len(keys) == 1 else "people"}, {len(named)} named in stories</text>')
        big = max(keys, key=lambda k: people[k]["amount"])
        note_from = 10 * 1000  # parameter: only rows this large get a "from one person" note
        if people[big]["amount"] > 0.5 * (a_n + a_u) and len(keys) > 1 and a_n + a_u >= note_from:
            svg.append(f'<text x="{x_bar}" y="{y + 60}" font-size="15" fill="{MUTED}">of which {money(people[big]["amount"])} from one person, '
                       f'{esc(person(people[big]["name"]))}</text>')
            y += 22
        ids += element("role bar", name, [r for k in keys for r in people[k]["rows"]])
        y += row_h
    svg.append("</svg>")
    all_people = set().union(*[keys for _, _, keys in fam_rows])
    total = sum(people[k]["amount"] for k in all_people)
    n_named = sum(people[k]["named"] for k in all_people)
    doc = shell(
        f"People holding roles in Muslim and Arab-advocacy groups gave {money(total)}; stories named {n_named} of {len(all_people)}",
        "Money from organizations named in the coverage and from people holding roles in them",
        "Top: what the organizations gave to the campaign and the pro-El-Sayed super PACs. Bottom: what people documented as their "
        "officers, directors or staff gave, split by whether any captured story named them.",
        legend([(BLUE, "Muslim organization"), (PURPLE, "Arab or Palestinian advocacy group"), (ORANGE, "people no story named")])
        + "\n".join(svg) + cite(ids),
        "<b>Source:</b> FEC filings of Abdul for U.S. Senate (net of refunds, through Sep 30, 2026) and of Fighting for Michigan PAC, "
        "Unity &amp; Justice Fund and MERIT PAC (through Aug 31, as amended through Oct 17); roles from the organizations' Form 990s, "
        "own pages and registries, each confirmed by the donor's own FEC employer entry or by an identity review on two attributes. "
        "<b>Not additive:</b> Unity &amp; Justice's gift to Fighting for Michigan includes money it received from CAIR Action, and a "
        "person with roles in two groups appears in both rows. <b>Not shown:</b> donors whose roles could not be confirmed, and "
        "organizations whose identity could not be documented.",
        W, h_svg + 330)
    return doc, h_svg + 330


# ---- figure 1b: the same money counted two ways ------------------------------------------------------------------
FOX_DATA_END = "20260715"   # parameter: last day of the campaign's pre-primary report, the newest filing before Fox's Aug 5 review


def fig_two_counts() -> tuple[str, int]:
    people = role_people()
    is_cair = lambda p: any(re.search(r"^CAIR|Council on American", o) for o, _ in p["orgs"])
    gifts = defaultdict(list)
    for r in map(json.loads, open(ROOT / "analysis" / "roster_named_itemized.jsonl", encoding="utf-8")):
        gifts[(r["last_norm"], r["first_norm"], (r["zip"] or "")[:5])].append(r)
    named_fec = {(" ".join(r["name_as_filed"].upper().split()), (r["city"] or "").upper()) for r in load("fec_rows")
                 if r["committee"] == "Abdul for U.S. Senate"}
    n_stories = {(" ".join(r["donor"].upper().split()), r["city"].upper(), r["state"]): r["n_stories_naming_donor"]
                 for r in load("donor_org_roles_confirmed")}
    named = lambda k: n_stories.get(k, 0) > 0 or (k[0], k[1]) in named_fec
    cair = {k: p for k, p in people.items() if is_cair(p) and p["campaign"]}
    other = {k: p for k, p in people.items() if not is_cair(p) and p["campaign"]}
    early = {}
    for k, p in cair.items():
        rows = [g for d in p["campaign"] for g in gifts.get((d["last_norm"], d["first_norm"], d["zip5"]), []) if g["date"] <= FOX_DATA_END]
        if any(g["amt"] > 0 for g in rows):
            early[k] = sum(g["amt"] for g in rows)
    net = lambda grp: sum(d["net"] for p in grp.values() for d in p["campaign"])
    short = {"ICNA and ICNA Relief": "ICNA", "Islamic Relief USA": "Islamic Relief", "KindHearts (closed 2006)": "KindHearts",
             "ACMER and its MERIT PAC": "ACMER", "Arab American PAC": "AAPAC", "U.S. Council of Muslim Organizations": "USCMO"}

    def groups_of(grp: dict) -> list[str]:
        """Organization families of a group of people, largest campaign total first."""
        tot = defaultdict(float)
        for p in grp.values():
            for f in {next(n for pat, n, _ in FAMILY if re.search(pat, o)) for o, _ in p["orgs"]}:
                tot[f] += sum(d["net"] for d in p["campaign"])
        return [short.get(f, f) for f, _ in sorted(tot.items(), key=lambda x: -x[1])]

    did = lambda grp: [donor_id(d) for p in grp.values() for d in p["campaign"]]
    pac = [r for p in people.values() for r in p["pac"]]
    big = max(people.values(), key=lambda p: sum(r["amount"] or 0 for r in p["pac"]))
    big_amt = sum(r["amount"] or 0 for r in big["pac"])
    fox = [c for c in load("claims") if c["entities"] == "CAIR-connected donors (group claim)" and c["published"]
           and c["outlet"] == "Fox News" and isinstance(c["amount_usd"], (int, float))]
    fox_first = min(c["published"] for c in fox)
    fox = [c for c in fox if c["published"] == fox_first]
    fox_amt = max(c["amount_usd"] for c in fox)
    fox_n = max(int(m) for c in fox for m in re.findall(r"at least (\d+)", c["quote"] or "")) if any("at least" in (c["quote"] or "") for c in fox) else None
    total_all = net(cair) + net(other) + sum(r["amount"] or 0 for r in pac)
    rows = [  # (title, definition, base, added, color, label, ids, hatch)
        ("What Fox reported", f"{date.fromisoformat(fox_first):%b %-d}; names not published", 0, fox_amt, GRAY,
         f"more than {money(fox_amt)} from at least {fox_n} people", [f"C{c['claim_id']}" for c in fox], True),
        ("Fox's definition, our records", f"gifts through {date(int(FOX_DATA_END[:4]), int(FOX_DATA_END[4:6]), int(FOX_DATA_END[6:])):%b %-d}, the newest filing before Fox's review",
         0, sum(early.values()), BLUE, f"{money(sum(early.values()))} from {len(early)} people; stories named {sum(named(k) for k in early)}",
         [donor_id(d) for k in early for d in cair[k]["campaign"]], False),
        ("Fox's definition, our records", "all gifts through Sep 30", 0, net(cair), BLUE,
         f"{money(net(cair))} from {len(cair)} people; stories named {sum(named(k) for k in cair)}", did(cair), False),
        ("+ other Muslim and Arab-advocacy groups", ", ".join(groups_of(other)), net(cair), net(other), PURPLE,
         f"{money(net(cair) + net(other))} from {len(cair) + len(other)} people (+{len(other)}); stories named {sum(named(k) for k in other)} of the new",
         did(other), False),
        ("+ gifts by people with these roles to PACs", f"{money(big_amt)} of it from {person(big['name'])}, reported in many stories", net(cair) + net(other),
         sum(r["amount"] or 0 for r in pac), ORANGE, f"{money(total_all)} in all", [receipt_id(r) for r in pac], False),
    ]
    x0, bw, row_h = 820, W - 120 - 820 - 520, 118
    scale = bw / total_all
    h_svg = 30 + len(rows) * row_h + 60
    svg, ids = [f'<svg width="{W - 120}" height="{h_svg}" viewBox="0 0 {W - 120} {h_svg}">',
                '<defs><pattern id="hatch" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                f'<rect width="12" height="12" fill="{LGRAY}"/><line x1="0" y1="0" x2="0" y2="12" stroke="{GRAY}" stroke-width="6"/></pattern></defs>'], []
    for i, (title, sub, base, add, col, label, rr, hatch) in enumerate(rows):
        y = 30 + i * row_h
        if i == 1:
            svg.append(f'<line x1="0" y1="{y - 22}" x2="{W - 120}" y2="{y - 22}" stroke="{AXIS}"/>')
        svg.append(f'<text x="0" y="{y + 30}" font-size="22" font-weight="bold" fill="{INK}">{esc(title)}</text>'
                   f'<text x="0" y="{y + 58}" font-size="17" fill="{MUTED}">{esc(sub)}</text>')
        if base:
            svg.append(f'<rect x="{x0}" y="{y + 8}" width="{base * scale:.1f}" height="54" fill="{LGRAY}"/>')
        svg.append(f'<rect x="{x0 + base * scale:.1f}" y="{y + 8}" width="{add * scale:.1f}" height="54" '
                   f'fill="{"url(#hatch)" if hatch else col}"/>'
                   f'<text x="{x0 + (base + add) * scale + 14:.1f}" y="{y + 42}" font-size="20" font-weight="bold" fill="{INK}">{esc(label)}</text>')
        ids += element("bar", title + " " + sub, rr)
    svg.append(f'<line x1="{x0}" y1="14" x2="{x0}" y2="{h_svg - 40}" stroke="{AXIS}"/></svg>')
    share_big = round(100 * big_amt / total_all)
    doc = shell(
        f"Counted Fox's way, CAIR staff and leaders gave El-Sayed's campaign about {money(round(net(cair), -3))}; the {money(round(total_all, -3))} total "
        f"adds other groups and PAC gifts, {share_big}% of it from one donor",
        "The same money, counted two ways",
        "Fox's definition: people who work or worked for CAIR, or held leadership roles there, and their gifts to the campaign. The "
        "broader count adds people with roles in the other Muslim and Arab-advocacy groups the coverage names, and those people's "
        "gifts to the PACs backing El-Sayed (the super PACs Fighting for Michigan and Unity &amp; Justice, and ACMER's MERIT PAC). Each bar is a running total; the colored part is what that step adds.",
        legend([(GRAY, "as Fox reported it"), (BLUE, "CAIR staff and leaders, to the campaign"), (PURPLE, "other groups' staff and leaders, to the campaign"),
                (ORANGE, "their gifts to PACs")]) + "\n".join(svg) + cite(ids),
        "<b>Source:</b> FEC filings of Abdul for U.S. Senate (net of refunds, through Sep 30, 2026) and of Fighting for Michigan, Unity "
        "&amp; Justice and MERIT PAC; roles from the organizations' own filings and pages, each confirmed on two attributes. Fox did "
        "not say which filings it used or publish its list, so how many of our people Fox counted is unknown; we count fewer than Fox "
        "in its window because we keep only roles we could confirm. The cut at Fox's date matches each donor's dated gifts by name and "
        "ZIP code. \"Stories named\": any captured story printed the person's name. KindHearts' assets were frozen by Treasury in 2006 "
        "pending investigation; that says nothing about the person who chaired it earlier.",
        W, h_svg + 410)
    return doc, h_svg + 410


# ---- figure 7: three panels: the money counted two ways, the maximum donors by name, the groups ------------------
WC = 2400   # parameter: this figure's page width (two panels over one)
GROUP_TEXT = {  # what the saved records show about each organization family (ties judged against primary records)
    "CAIR (national and chapters)": ("CAIR", "Council on American-Islamic Relations and its chapters and CAIR Action. Named in 2007 on prosecutors' "
                                     "list of unindicted co-conspirators in the Holy Land Foundation Hamas-financing case; never charged. "
                                     "Listed as a terrorist group by the UAE in 2014; labeled one by Texas and Florida in 2025."),
    "KindHearts (closed 2006)": ("KindHearts", "Toledo charity, now closed. Treasury froze its assets in 2006 \"pending investigation\", calling it "
                                 "tied to Hamas; it was never formally designated. The donor was its chairman in 2002-03."),
    "ACMER and its MERIT PAC": ("ACMER", "American Committee for Middle East Rights, an advocacy group, and its MERIT PAC. The donor is its "
                                "executive director."),
    "Emgage": ("Emgage", "Muslim American civic and voter-turnout group. The donor is a state political director."),
    "ICNA and ICNA Relief": ("ICNA", "Islamic Circle of North America and its relief arm. Named in a 1991 Muslim Brotherhood memo, a Holy "
                             "Land trial exhibit, on a list headed \"our organizations and the organizations of our friends\"."),
    "Islamic Relief USA": ("Islamic Relief USA", "Humanitarian charity. Its international parent, Islamic Relief Worldwide, was banned by "
                           "Israel in 2014. The donors are its CEO and a fundraiser."),
    "MPower Change": ("MPower Change", "Muslim grassroots advocacy group; published a 2018 report with CAIR."),
    "Arab American PAC": ("AAPAC", "Arab American Political Action Committee, Dearborn. The donor is its president."),
    "IMEU": ("IMEU", "Institute for Middle East Understanding, a Palestinian-focused communications group. The donor is its executive director."),
    "U.S. Council of Muslim Organizations": ("USCMO", "U.S. Council of Muslim Organizations, an umbrella group. The donor is its secretary general."),
    "Unity & Justice Fund (super PAC CAIR Action helps fund)": ("Unity & Justice Fund", "Super PAC that CAIR Action helps fund; it gave "
                                                                "to Fighting for Michigan. The donor, a CAIR executive director, was its treasurer until 2025."),
}
GROUP_TIES = {"CAIR": r"^(CAIR|Council (on|for) American)", "ICNA": r"ICNA|Islamic Circle", "Islamic Relief USA": r"Islamic Relief",
              "MPower Change": r"MPower", "Unity & Justice Fund": r"^Unity & Justice"}
NAME_SLICES = [("ARABIC", "Arabic names", BLUE), ("SOUTH_ASIAN_MUSLIM", "South Asian Muslim names", "#5b9be4"),
               ("AM-other", "Other Muslim names", BLUE250), ("other", "Other names", LGRAY),
               ("uncertain", "Can't tell from the name", GRAY)]


def max_donors_by_name() -> tuple[list, dict]:
    """The donors at the limit, each name sorted into one heritage group (a confident judgment, or 'uncertain')."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("nos", ROOT / "scripts" / "name_origin_share.py")
    nos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nos)
    judge = nos.load_judge()
    top = [d for d in map(json.loads, open(ROOT / "analysis" / "donors_net.jsonl", encoding="utf-8")) if d["net"] >= LIMIT - 0.005]
    groups = defaultdict(list)
    for d in top:
        j = judge(d["name"])
        if j["lo"] >= nos.CONFIDENT:
            k = j["origin"] if j["origin"] in ("ARABIC", "SOUTH_ASIAN_MUSLIM") else "AM-other"
        else:
            k = "other" if j["hi"] <= 1 - nos.CONFIDENT else "uncertain"
        groups[k].append(d)
    return top, groups


def fig_combo() -> tuple[str, int]:
    import math
    import textwrap
    fam_of = lambda p: {next(n for pat, n, _ in FAMILY if re.search(pat, o)) for o, _ in p["orgs"]}
    CAIR = "CAIR (national and chapters)"
    folks = [p for p in persons(role_people()) if p["campaign"] or p["pac"]]
    camp = lambda grp: sum(d["net"] for p in grp for d in p["campaign"])
    pacs = lambda grp: sum(r["amount"] or 0 for p in grp for r in p["pac"])
    rows_of = lambda grp: [donor_id(d) for p in grp for d in p["campaign"]] + [receipt_id(r) for p in grp for r in p["pac"]]
    total = camp(folks) + pacs(folks)
    svg, ids = [], []

    # left: the donors at the limit (the figure-6 panel, same format)
    tiers = json.loads((ROOT / "analysis" / "name_origin_share.json").read_text(encoding="utf-8"))["by_donor_tier"]
    m = tiers["at_7000_max"]
    top = [d for d in map(json.loads, open(ROOT / "analysis" / "donors_net.jsonl", encoding="utf-8")) if d["net"] >= LIMIT - 0.005]
    assert m["n_donors"] == len(top), "name_origin_share.json is out of date"
    k = round(m["expected_pct_of_donors"])
    cell, gap = 54, 8
    svg.append(f'<text x="0" y="30" font-size="26" font-weight="bold" fill="{INK}">The {len(top):,} who gave {money(LIMIT)}, the maximum</text>')
    for i in range(100):
        r_, c_ = divmod(i, 10)
        svg.append(f'<rect x="{c_ * (cell + gap)}" y="{60 + r_ * (cell + gap)}" width="{cell}" height="{cell}" rx="4" fill="{BLUE if i < k else LGRAY}"/>')
    tx = 10 * (cell + gap) + 30
    svg.append(f'<text x="{tx}" y="{60 + 150}" font-size="128" font-weight="bold" fill="{BLUE}">{k}%</text>'
               f'<text x="{tx}" y="{60 + 200}" font-size="24" fill="{INK}">of these donors have</text>'
               f'<text x="{tx}" y="{60 + 230}" font-size="24" fill="{INK}">Arab- or Muslim-heritage names</text>'
               f'<text x="{tx}" y="{60 + 290}" font-size="22" fill="{MUTED}">They gave {round(m["expected_pct_of_net_dollars"])}% of</text>'
               f'<text x="{tx}" y="{60 + 318}" font-size="22" fill="{MUTED}">the group\'s dollars</text>'
               f'<rect x="0" y="{60 + 10 * (cell + gap) + 10}" width="18" height="18" rx="4" fill="{BLUE}"/>'
               f'<text x="28" y="{60 + 10 * (cell + gap) + 25}" font-size="18" fill="{INK}">Arab- or Muslim-heritage name</text>'
               f'<rect x="310" y="{60 + 10 * (cell + gap) + 10}" width="18" height="18" rx="4" fill="{LGRAY}"/>'
               f'<text x="338" y="{60 + 10 * (cell + gap) + 25}" font-size="18" fill="{INK}">other names (each square is 1% of these donors)</text>')
    ids += element("waffle", "donors at the limit", [donor_id(d) for d in top])

    # center: the money from people with roles in the groups, one slice per group, sized by dollars
    x0c = 1150
    first = lambda p: CAIR if CAIR in fam_of(p) else sorted(fam_of(p))[0]     # each person once: CAIR first
    by_g = defaultdict(list)
    for p in folks:
        by_g[first(p)].append(p)
    small = sorted([g for g in by_g if g != CAIR], key=lambda g: -(camp(by_g[g]) + pacs(by_g[g])))
    svg.append(f'<text x="{x0c}" y="64" font-size="68" font-weight="bold" fill="{INK}">{money(total)}</text>'
               f'<text x="{x0c}" y="100" font-size="22" fill="{INK}">from {len(folks)} people with roles in these groups,</text>'
               f'<text x="{x0c}" y="128" font-size="22" fill="{INK}">to El-Sayed\'s campaign and the PACs backing him</text>')
    cx, cy, ro, ri = x0c + 330, 450, 230, 140
    a0 = 0.0
    lab_y = 190
    shades = {"muslim": [BLUE250, "#5b9be4", "#9ec5f2", "#3f86dc", "#b9d5f5"], "arab": [PURPLE, "#a08ae6", "#c3b5f0"]}
    used = defaultdict(int)
    kind = {name: kd for _, name, kd in FAMILY}
    slice_col = {}
    for g in small + [CAIR]:
        grp = by_g[g]
        v = camp(grp) + pacs(grp)
        a1 = a0 + 2 * math.pi * v / total
        if g == CAIR:
            col = BLUE
        else:
            pal = shades[kind[g]]
            col = pal[used[kind[g]] % len(pal)]
            used[kind[g]] += 1
        slice_col[g] = col
        pt = lambda a, rr: (cx + rr * math.sin(a), cy - rr * math.cos(a))
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = pt(a0, ro), pt(a1, ro), pt(a1, ri), pt(a0, ri)
        big = 1 if a1 - a0 > math.pi else 0
        svg.append(f'<path d="M{x1:.2f},{y1:.2f} A{ro},{ro} 0 {big} 1 {x2:.2f},{y2:.2f} L{x3:.2f},{y3:.2f} A{ri},{ri} 0 {big} 0 {x4:.2f},{y4:.2f} Z" '
                   f'fill="{col}" stroke="{BG}" stroke-width="{1.5 if g == CAIR else 0.6}"/>')
        n = len(grp)
        who = f"{n} {'person' if n == 1 else 'people'} · {money(v)}"
        short = GROUP_TEXT[g][0]
        mx, my = pt((a0 + a1) / 2, ro)
        if g == CAIR:
            yb = cy + ro + 56
            lead = max(grp, key=lambda p: sum(r["amount"] or 0 for r in p["pac"]))
            svg.append(f'<text x="{cx}" y="{yb}" font-size="24" font-weight="bold" fill="{INK}" text-anchor="middle">{esc(short)} · {esc(who)}</text>'
                       f'<text x="{cx}" y="{yb + 28}" font-size="18" fill="{MUTED}" text-anchor="middle">{money(pacs(grp))} of it to PACs, '
                       f'{money(sum(r["amount"] or 0 for r in lead["pac"]))} of that from {esc(person(lead["name"]))}</text>')
        else:
            lx = cx + ro + 60
            svg.append(f'<polyline points="{mx:.1f},{my:.1f} {lx - 40:.1f},{lab_y - 6:.1f} {lx - 8:.1f},{lab_y - 6:.1f}" fill="none" stroke="{MUTED}" stroke-width="1"/>'
                       f'<text x="{lx}" y="{lab_y}" font-size="19" fill="{INK}"><tspan font-weight="bold">{esc(short)}</tspan> · {esc(who)}</text>')
            lab_y += 34
        ids += element("slice", short, rows_of(grp))
        a0 = a1

    # right: the groups
    y_top = 800                                   # where the bottom half starts
    svg.append(f'<text x="0" y="{y_top + 52}" font-size="26" font-weight="bold" fill="{INK}">The groups</text>')
    fams = defaultdict(list)
    for p in folks:
        for f in fam_of(p):
            fams[f].append(p)
    assert set(fams) <= set(GROUP_TEXT), f"no description for {set(fams) - set(GROUP_TEXT)}"
    order = sorted(fams, key=lambda f: (f != CAIR, f != "KindHearts (closed 2006)", -(camp(fams[f]) + pacs(fams[f]))))
    all_ties = load("ties")
    wrap, lh, gap_b, top_y = 118, 27, 26, y_top + 92        # 20 px text wrapped to fill a 1,100 px column
    lines = {f: textwrap.wrap(GROUP_TEXT[f][1], wrap) for f in order}
    height = lambda f: 30 + lh * len(lines[f]) + gap_b
    half = sum(height(f) for f in order) / 2
    col_x, y, done, bottom = 0, top_y, 0.0, 0.0
    for f in order:
        if col_x == 0 and done >= half - height(f) / 2:
            col_x, y = 1170, top_y                        # the second column
        done += height(f)
        short = GROUP_TEXT[f][0]
        grp = fams[f]
        amount = (f"{len(grp)} {'person' if len(grp) == 1 else 'people'} · {money(camp(grp))} to the campaign"
                  + (f", {money(pacs(grp))} to PACs" if pacs(grp) else ""))
        block = 30 + lh * len(lines[f])
        svg.append(f'<rect x="{col_x}" y="{y - 22}" width="7" height="{block}" rx="3" fill="{slice_col.get(f, SLATE)}"/>'
                   f'<text x="{col_x + 20}" y="{y}" font-size="23" font-weight="bold" fill="{INK}">{esc(short)}'
                   f'<tspan font-weight="normal" font-size="21" fill="{INK}">  {esc(amount)}</tspan></text>')
        for i, line in enumerate(lines[f]):
            svg.append(f'<text x="{col_x + 20}" y="{y + 30 + i * lh}" font-size="20" fill="{MUTED}">{esc(line)}</text>')
        tie_ids = [f"T{t['tie_id']}" for t in all_ties if short in GROUP_TIES and re.search(GROUP_TIES[short], t["entity"] or "")
                   and t["link_type"] in ("designation", "listed_in_document", "other")]
        ids += element("group", short, rows_of(grp) + tie_ids)
        y += block + gap_b
        bottom = max(bottom, y)
    h_svg = bottom
    svg = [f'<svg width="{WC - 120}" height="{h_svg}" viewBox="0 0 {WC - 120} {h_svg}">'] + svg + [
        f'<line x1="1110" y1="0" x2="1110" y2="{y_top - 10}" stroke="{AXIS}"/><line x1="0" y1="{y_top + 10}" x2="{WC - 120}" '
        f'y2="{y_top + 10}" stroke="{AXIS}"/></svg>']
    doc = shell(
        f"People with roles in CAIR and other Muslim and Arab-advocacy groups gave {money(total)} to El-Sayed's campaign and the PACs "
        f"backing him; {k}% of his maximum donors have Arab- or Muslim-heritage names",
        "El-Sayed's donors and the groups in the coverage", "",
        "\n".join(svg) + cite(ids),
        "<b>How the links were made:</b> a donor counts as staff or a leader of a group when the group's own records name them (its IRS "
        "filings, website, annual reports or FEC filings) or when the donor's own FEC filing gives the group as employer, and only when "
        "the record and the donor match on at least two details, such as name and city or name and employer. In the ring, each person "
        "counts once, under CAIR if they also hold a role elsewhere; below, a person with roles in two groups is listed under both. "
        "<b>Money:</b> FEC filings of El-Sayed's campaign (net of refunds, through Sep 30, 2026) and of the PACs Fighting for Michigan, "
        "Unity &amp; Justice and MERIT PAC (through Aug 31). <b>The groups:</b> from the Holy Land Foundation case filings and the 1991 "
        "memo entered as a trial exhibit, Treasury's 2006 notice on KindHearts, the UAE's 2014 list, the Texas and Florida orders, "
        "Israel's 2014 order and the groups' own publications. <b>Names (top left):</b> each donor's name is judged by its heritage (Arabic, "
        "South Asian Muslim, Persian, Turkish and other Muslim traditions), not by religion: Arab Christians count and Muslims with names "
        "from other traditions do not. That panel says nothing about any donor's ties to the groups.",
        WC, h_svg + 300)
    return doc, h_svg + 300


# ---- figure 2: how Jukaku's super PAC money was described -----------------------------------------------------------
def fig_jukaku() -> tuple[str, int]:
    claims = [c for c in load("claims") if "Tayeb Jukaku" in (c["entities"] or "").split("; ")
              and c["link_type"] in ("donated_to_campaign", "donated_to_super_pac")]
    fec = [r for r in load("fec_rows") if r["entity"] == "Tayeb Jukaku"]
    ffm = sorted([r for r in fec if r["committee"] == "Fighting for Michigan PAC"], key=lambda r: r["date"])
    uj = [r for r in fec if r["committee"] == "Unity & Justice Fund"]
    camp_net = sum(r["amount"] for r in fec if r["committee"] == "Abdul for U.S. Senate")
    d0, d1 = date(2026, 1, 1), date(2026, 10, 31)
    x0, x1 = 420, W - 160
    X = lambda d: x0 + (x1 - x0) * ((d - d0).days / (d1 - d0).days)
    lanes = [("Fighting for Michigan PAC", "Fighting for Michigan PAC"), ("unnamed super PAC supporting El-Sayed", "a super PAC (unnamed)"),
             ("Unity & Justice Fund", "Unity & Justice Fund"), ("Abdul for U.S. Senate", "El-Sayed's campaign itself"),
             ("unspecified", "no recipient stated")]

    # when each gift became public: the receipt date of the first filing that lists it
    raw = Path("/mnt/data/projects/elsayed/openfec_pacs_dl")
    filed = {f["file_number"]: f["receipt_date"][:10] for f in json.loads((raw / "ffm_filings.json").read_text())}
    pac = json.loads((raw / "rows" / "ffm_A.json").read_text())
    first_seen = defaultdict(list)
    for r in pac["efile"] + pac["processed"]:
        if r.get("file_number") in filed:
            first_seen[r["transaction_id"]].append(filed[r["file_number"]])
    public = {r["transaction_id"]: min(first_seen[r["transaction_id"]]) for r in ffm if first_seen[r["transaction_id"]]}

    def cum_ffm(d: date) -> float:
        """What the PAC's filings showed on day d."""
        return sum(r["amount"] for r in ffm if r["transaction_id"] in public and date.fromisoformat(public[r["transaction_id"]]) <= d)

    def color(c: dict) -> tuple[str, str]:
        amt, rec = c["amount_usd"], c["recipient_norm"]
        if rec == "Unity & Justice Fund":
            return LGRAY, "a filing exists; donor identity unconfirmed"
        if rec == "unspecified":
            return GRAY, "no recipient stated"
        if rec == "Abdul for U.S. Senate":
            if not isinstance(amt, (int, float)):
                return AQUA, "matches the filings"           # he did give to the campaign
            return (RED, "contradicts the filings") if amt > camp_net else (AQUA, "matches the filings")
        if not isinstance(amt, (int, float)) or not c["published"]:
            return AQUA, "matches the filings"               # he did give to the super PAC
        have = cum_ffm(date.fromisoformat(c["published"]))
        return (AQUA, "matches the filings") if abs(amt - have) < 1 else (YELLOW, "an earlier total") if amt < have else (RED, "contradicts the filings")

    lane_h, top = 150, 190
    h_svg = top + len(lanes) * lane_h + 70
    svg, ids, nodate = [f'<svg width="{W - 120}" height="{h_svg}" viewBox="0 0 {W - 120} {h_svg}">'], [], 0
    for m in range(1, 11):
        x = X(date(2026, m, 1))
        svg.append(f'<line x1="{x:.1f}" y1="40" x2="{x:.1f}" y2="{h_svg - 40}" stroke="{GRID}"/>'
                   f'<text x="{x + 4:.1f}" y="{h_svg - 14}" font-size="16" fill="{MUTED}">{date(2026, m, 1):%b}</text>')
    svg.append(f'<text x="0" y="70" font-size="20" font-weight="bold" fill="{INK}">What the filings show</text>'
               f'<text x="0" y="96" font-size="16" fill="{MUTED}">Campaign, all years: {money(camp_net)} net</text>')
    run = 0.0
    for r in ffm:
        run += r["amount"]
        x = X(date.fromisoformat(r["date"]))
        pub = public.get(r["transaction_id"])
        svg.append(f'<rect x="{x - 6:.1f}" y="62" width="12" height="34" fill="{INK}"/>'
                   f'<text x="{x + 12:.1f}" y="76" font-size="16" fill="{INK}">{money(r["amount"])} to FFM, total {money(run)}</text>'
                   f'<text x="{x + 12:.1f}" y="96" font-size="15" fill="{MUTED}">made public {date.fromisoformat(pub):%b %-d}</text>' if pub else "")
        if pub:
            xp = X(date.fromisoformat(pub))
            svg.append(f'<line x1="{xp:.1f}" y1="100" x2="{xp:.1f}" y2="{h_svg - 40}" stroke="{INK}" stroke-dasharray="6 6" opacity="0.5"/>')
        ids += element("filing mark", f"FFM receipt {r['date']}", [f"R:FFM:{r['transaction_id']}"])
    for r in uj:
        x = X(date.fromisoformat(r["date"]))
        svg.append(f'<rect x="{x - 6:.1f}" y="118" width="12" height="34" fill="{GRAY}"/>'
                   f'<text x="{x + 12:.1f}" y="132" font-size="16" fill="{INK}">{money(r["amount"])} to U&amp;J under the same name</text>'
                   f'<text x="{x + 12:.1f}" y="152" font-size="15" fill="{MUTED}">filed from {esc(r["city"].title())}, {esc(r["state"])}: identity unconfirmed</text>')
        ids += element("filing mark", f"U&J receipt {r['date']}", [f"R:UJF:{r['transaction_id']}"])
    for li, (key, label) in enumerate(lanes):
        y = top + li * lane_h
        lane_claims = [c for c in claims if c["recipient_norm"] == key]
        svg.append(f'<line x1="0" y1="{y}" x2="{W - 120}" y2="{y}" stroke="{AXIS}"/>'
                   f'<text x="0" y="{y + 34}" font-size="20" font-weight="bold" fill="{INK}">{esc(label)}</text>'
                   f'<text x="0" y="{y + 60}" font-size="16" fill="{MUTED}">{len(lane_claims)} claims</text>')
        stack = Counter()
        for c in sorted(lane_claims, key=lambda c: c["published"] or ""):
            if not c["published"]:
                nodate += 1
                continue
            d = date.fromisoformat(c["published"])
            b = (d - d0).days // 4
            k = stack[b]
            stack[b] += 1
            col, _ = color(c)
            cx, cy = X(d), y + 28 + (k % 9) * 13
            svg.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="6" fill="{col}" stroke="{INK}" stroke-width="0.6"/>')
            ids += element("claim dot", f"{label} {c['published']}", [f"C{c['claim_id']}"])
    svg.append("</svg>")
    n_story = len({c["story_id"] for c in claims})
    tally = Counter(color(c)[1] for c in claims)
    wrong = [c for c in claims if color(c)[1] == "contradicts the filings"]
    wrong_text = Counter(re.sub(r"\W+", " ", (c["quote"] or "").lower()).strip() for c in wrong)
    same = max(wrong_text.values()) if wrong_text else 0
    doc = shell(
        f"Most stories placed Jukaku's money where the filings put it; {tally['contradicts the filings']} claims moved it into the campaign",
        "Tayeb Jukaku's political money, as filed and as reported",
        f"Top: his receipts as the committees filed them. Below: each of {len(claims)} claims about his gifts in {n_story} stories, "
        "at its publication date, in the lane of the recipient the story named. Color compares the amount the story gave with what the "
        "filings showed on that date; dashed lines mark when each gift became public.",
        legend([(AQUA, f"consistent with the filings ({tally['matches the filings']})"), (YELLOW, f"an earlier, lower total ({tally['an earlier total']})"),
                (RED, f"contradicts the filings ({tally['contradicts the filings']})"), (LGRAY, f"filing exists, identity unconfirmed ({tally['a filing exists; donor identity unconfirmed']})"),
                (GRAY, f"no recipient stated ({tally['no recipient stated']})")])
        + "\n".join(svg) + cite(ids),
        "<b>Source:</b> FEC filings of Fighting for Michigan PAC, Unity &amp; Justice Fund and Abdul for U.S. Senate; claims "
        f"extracted verbatim from captured stories. {nodate} claims without a publication date are counted in the lanes but not drawn. "
        f"Of the claims that contradict the filings, {same} carry the same sentence (one syndicated column). A claim with no amount is "
        "counted as consistent when the recipient it names did receive money from him. A gift's public date is the filing date of the "
        "earliest filing held that lists it (the first two may already have appeared in the original Q1 report of April 13). "
        "<b>Not shown:</b> whether the Unity &amp; Justice donor is the same person (the filing gives a different city and no "
        "occupation); this figure makes no claim about why stories differed.",
        W, h_svg + 400)
    return doc, h_svg + 400


# ---- figure 3: which kinds of claims held up ---------------------------------------------------------------------
GROUPS = [("Gave to the campaign", ("donated_to_campaign",), "gifts to the campaign"),
          ("Gave to a super PAC", ("donated_to_super_pac",), "gifts to super PACs"),
          ("Holds an office in a group", ("leader_of",), "offices held"), ("Works or worked for a group", ("employee_of",), "jobs"),
          ("Belongs to a group", ("member_of",), "membership"), ("Is related to someone in a group", ("family_of",), "family ties"),
          ("Named in a document or list", ("listed_in_document",), "documents and lists"),
          ("Convicted or sentenced", ("convicted_or_sentenced",), "convictions"),
          ("A group's terror designation", ("designation",), "designations"), ("Spoke at or hosted an event", ("hosted_or_spoke",), "events"),
          ("Endorsed or praised", ("endorsed", "praised"), "endorsements and praise"), ("Other ties", ("other", "staff", "statement"), "other ties")]
VCOL = [("holds_up", AQUA, "holds up"), ("holds_up_partly", YELLOW, "holds up partly"), ("unsupported", GRAY, "unsupported"),
        ("contradicted", RED, "contradicted"), ("about_someone_else", PURPLE, "about someone else")]


def fig_verdicts() -> tuple[str, int]:
    ties = [t for t in load("ties") if not t["verdict"].startswith("statement")]
    share = lambda kinds, v: sum(t["verdict"] == v for t in ties if t["link_type"] in kinds) / max(1, sum(t["link_type"] in kinds for t in ties))
    groups = sorted(GROUPS, key=lambda g: -share(g[1], "holds_up") - 0.5 * share(g[1], "holds_up_partly"))
    unsupported_pct = lambda g: round(100 * share(g[1], "unsupported"))
    row_h, top, label_w = 74, 40, 520
    bar_w = W - 120 - label_w - 160
    h_svg = top + len(GROUPS) * row_h + 20
    svg, ids = [f'<svg width="{W - 120}" height="{h_svg}" viewBox="0 0 {W - 120} {h_svg}">'], []
    for i, (label, kinds, _) in enumerate(groups):
        ts = [t for t in ties if t["link_type"] in kinds]
        y = top + i * row_h
        svg.append(f'<text x="0" y="{y + 36}" font-size="21" fill="{INK}">{esc(label)}</text>')
        x = label_w
        for key, col, name in VCOL:
            part = [t for t in ts if t["verdict"] == key]
            if not part:
                continue
            w = bar_w * len(part) / len(ts)
            svg.append(f'<rect x="{x:.1f}" y="{y + 8}" width="{w:.1f}" height="44" fill="{col}"/>')
            if w > 34:
                svg.append(f'<text x="{x + w / 2:.1f}" y="{y + 37}" font-size="18" text-anchor="middle" fill="{INK}" font-weight="bold">{len(part)}</text>')
            ids += element("segment", f"{label}: {name}", [f"T{t['tie_id']}" for t in part])
            x += w
        svg.append(f'<text x="{label_w + bar_w + 16}" y="{y + 37}" font-size="18" fill="{MUTED}">{len(ts)} ties</text>')
    svg.append("</svg>")
    held = sum(t["verdict"] == "holds_up" for t in ties)
    unsup = sum(t["verdict"] == "unsupported" for t in ties)
    worst = sorted(groups, key=lambda g: -share(g[1], "unsupported"))[:2]
    doc = shell(
        f"Claims about money and positions mostly hold up; for {worst[0][2]} and {worst[1][2]}, "
        f"{unsupported_pct(worst[0])}% and {unsupported_pct(worst[1])}% have no record behind them",
        "Every factual tie in the coverage, checked against primary records",
        f"Each bar is one kind of claimed tie; each segment counts distinct ties by verdict. Of {len(ties)} factual ties, "
        f"{held} hold up and {unsup} are unsupported by any primary record found.",
        legend([(c, n) for _, c, n in VCOL]) + "\n".join(svg) + cite(ids),
        "<b>Source:</b> claims extracted verbatim from captured stories; each distinct tie judged against saved primary records "
        "(court records, government designations, IRS filings, FEC filings, the organizations' own pages, the person's own words), "
        "reviewed adversarially by a second engine, with every disagreement decided in writing. <b>Unsupported</b> means no "
        "primary record was found, not that the claim is false. Statements (what someone said) are not included.",
        W, h_svg + 360)
    return doc, h_svg + 360


# ---- figure 4: how the CAIR donor figure was described as it spread ---------------------------------------------------
CAT = [(r"(connected|tied|linked)[^.]{0,40}Hamas|Hamas[- ]linked (donors|individuals)|Hamas fundrais", RED, "donors described as tied to Hamas"),
       (r"\bmembers?\b", YELLOW, "'members' of CAIR"),
       (r"linked|connected|tied|associated|affiliat|connection", ORANGE, "'linked', 'connected' or 'tied' to CAIR"),
       (r"work|employ|staff|lead|official|board|officer|executive|chair|treasurer", AQUA, "work or worked for, or led, CAIR (Fox's definition)")]
TERROR_LABEL = r"terror|Hamas"


def fig_cair() -> tuple[str, int]:
    since = "2026-08-01"  # parameter: this cycle's coverage (earlier 2018 claims concern the governor's race)
    cl = [c for c in load("claims") if c["entities"] == "CAIR-connected donors (group claim)" and (c["published"] or "") >= since]
    stories = {s["story_id"]: s for s in load("stories")}
    per = {}
    for c in sorted(cl, key=lambda c: (c["published"], c["claim_id"])):
        per.setdefault(c["story_id"], c)
    items = sorted(per.values(), key=lambda c: (c["published"], c["outlet"] or ""))
    d0 = date.fromisoformat(min(c["published"] for c in items))
    d1 = date.fromisoformat(max(c["published"] for c in items))
    x0, x1 = 560, W - 360
    span = max(1, (d1 - d0).days)
    X = lambda d: x0 + (x1 - x0) * ((d - d0).days / span)
    row_h, top = 30, 46
    h_svg = top + len(items) * row_h + 50
    svg, ids = [f'<svg width="{W - 120}" height="{h_svg}" viewBox="0 0 {W - 120} {h_svg}">'], []
    d = d0
    while d <= d1:
        if d.day in (1, 8, 15, 22):
            x = X(d)
            svg.append(f'<line x1="{x:.1f}" y1="20" x2="{x:.1f}" y2="{h_svg - 30}" stroke="{GRID}"/>'
                       f'<text x="{x + 4:.1f}" y="{h_svg - 8}" font-size="15" fill="{MUTED}">{d:%b %-d}</text>')
        d = date.fromordinal(d.toordinal() + 1)
    counts = Counter()
    for i, c in enumerate(items):
        y = top + i * row_h
        q = c["quote"] or ""
        col, name = next(((col, name) for pat, col, name in CAT if re.search(pat, q, re.I)), (GRAY, "other wording"))
        counts[name] += 1
        ring = bool(re.search(TERROR_LABEL, q, re.I)) and name != "donors described as tied to Hamas"
        counts["terror label on CAIR"] += ring
        outlet = (c["outlet"] or stories.get(c["story_id"], {}).get("outlet") or "")[:38]
        amt = money(c["amount_usd"]) if isinstance(c["amount_usd"], (int, float)) else ""
        x = X(date.fromisoformat(c["published"]))
        svg.append(f'<text x="0" y="{y + 6}" font-size="16" fill="{INK}">{esc(outlet)}</text>'
                   f'<line x1="{x0}" y1="{y}" x2="{x - 9:.1f}" y2="{y}" stroke="{LGRAY}"/>'
                   f'<circle cx="{x:.1f}" cy="{y}" r="8" fill="{col}" stroke="{INK}" stroke-width="{4 if ring else 0.6}"/>'
                   f'<text x="{x + 14:.1f}" y="{y + 6}" font-size="15" fill="{MUTED}">{esc(amt)}</text>')
        ids += element("story dot", f"{outlet} {c['published']}", [f"C{c['claim_id']}"])
    # identical sentences in three or more stories (syndicated copies): bracket them
    norm = lambda q: re.sub(r"\W+", " ", (q or "").lower()).strip()
    groups = defaultdict(list)
    for i, c in enumerate(items):
        groups[norm(c["quote"])].append(i)
    for idx in groups.values():
        if len(idx) >= 3 and max(idx) - min(idx) == len(idx) - 1:
            ya, yb = top + min(idx) * row_h - 10, top + max(idx) * row_h + 10
            svg.append(f'<path d="M{W - 330},{ya} h14 v{yb - ya} h-14" fill="none" stroke="{MUTED}" stroke-width="2"/>'
                       f'<text x="{W - 306}" y="{(ya + yb) / 2 + 6:.1f}" font-size="16" fill="{MUTED}">same text, {len(idx)} outlets</text>')
    svg.append("</svg>")
    first = items[0]
    precise = counts["work or worked for, or led, CAIR (Fox's definition)"]
    doc = shell(
        f"{len(items)} stories repeated Fox's CAIR-donor figure; {len(items) - precise} described the donors more loosely than Fox did",
        "One claim across the coverage",
        f"Each row is a story that repeated the figure (first: {esc(first['outlet'])}, {first['published']}), at its publication date. "
        "Color: how the story described the donors. Thick black ring: the same sentence also called CAIR a terrorist or Hamas-linked "
        f"group ({counts['terror label on CAIR']} stories). Right: the dollar figure the story gave.",
        legend([(col, f"{name} ({counts[name]})") for _, col, name in CAT] + [(GRAY, f"other wording ({counts['other wording']})")])
        + "\n".join(svg) + cite(ids),
        "<b>Source:</b> claims extracted verbatim from captured stories; one dot per story (its first claim about the group). The "
        "original Fox News Digital review defined the donors as people who work or worked for CAIR or held leadership roles "
        "there. Color follows the words of the quoted sentence, most charged wording first. <b>Not shown:</b> the list of donors "
        "itself, which no story published; our own reconstruction is in the private tables.",
        W, h_svg + 420)
    return doc, h_svg + 420


# ---- figure 5: how the money moved (receipts, and in version b what Fighting for Michigan spent) ----------------------
SINCE = "2025-01-01"   # parameter: the 2025-26 cycle, the window of the schedule A pull
SLATE = "#6f8fb0"


def role_people() -> dict:
    """People with confirmed roles in the figure-1 organization families: their campaign rows and super PAC receipts."""
    donors = [json.loads(l) for l in open(ROOT / "analysis" / "donors_net.jsonl", encoding="utf-8")]
    by_nc = defaultdict(list)
    for d in donors:
        by_nc[(" ".join(d["name"].upper().split()), d["city"].upper(), d["state"])].append(d)
    rec_by_nc = defaultdict(list)
    for r in load("super_pac_receipts"):
        if r["entity_type"] == "IND":
            rec_by_nc[(" ".join(r["contributor"].upper().replace(",", ", ").split()).replace(" ,", ","), (r["city"] or "").upper())].append(r)
    people = {}
    for r in load("donor_org_roles_confirmed"):
        fam = next((name for pat, name, _ in FAMILY if re.search(pat, r["org"])), None)
        key = (" ".join(r["donor"].upper().split()), r["city"].upper(), r["state"])
        if not fam:
            continue
        p = people.setdefault(key, {"name": r["donor"], "orgs": set(), "campaign": by_nc.get(key, []),
                                    "pac": rec_by_nc.get((" ".join(r["donor"].upper().replace(",", ", ").split()).replace(" ,", ","), r["city"].upper()), [])})
        p["orgs"].add((r["org"], r["roles"]))
        p.setdefault("ev", set()).update(e["sha256"] for e in r["evidence"] if isinstance(e, dict) and e.get("sha256"))
    return people


def persons(people: dict) -> list[dict]:
    """Records of one person counted once: same state and first name, and either the same surname confirmed by the same
    saved organization record, or a one-letter surname variant at the same city with the same self-reported employer."""
    keys = sorted(people)
    root = {k: k for k in keys}

    def find(k):
        while root[k] != k:
            k = root[k]
        return k
    name = lambda p: (re.sub("[^A-Z]", "", p["name"].upper().partition(",")[0]),
                      re.sub("[^A-Z]", "", (p["name"].upper().partition(",")[2].split() or [""])[0]))
    skel = lambda last: last[:1] + re.sub("[AEIOU]", "", last[1:])
    employer = lambda p: {r.split("/")[-1].strip().upper() for _, r in p["orgs"] if "/" in r}
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            pa, pb = people[a], people[b]
            (la, fa), (lb, fb) = name(pa), name(pb)
            if a[2] != b[2] or fa != fb:
                continue
            if (la == lb and pa["ev"] & pb["ev"]) or (a[1] == b[1] and skel(la) == skel(lb) and employer(pa) & employer(pb)):
                root[find(b)] = find(a)
    out = defaultdict(list)
    for k in keys:
        out[find(k)].append(k)
    merged = []
    for ks in out.values():
        ps = [people[k] for k in ks]
        camp = {donor_id(d): d for p in ps for d in p["campaign"]}
        pac = {receipt_id(r): r for p in ps for r in p["pac"]}
        merged.append({"name": ps[0]["name"], "orgs": set().union(*(p["orgs"] for p in ps)), "campaign": list(camp.values()),
                       "pac": list(pac.values())})
    return merged


def band(x0: float, a0: float, b0: float, x1: float, a1: float, b1: float, color: str, opacity: float = 0.0) -> str:
    """A pipe from the vertical segment (x0, a0..b0) to (x1, a1..b1)."""
    xm = (x0 + x1) / 2
    opacity = opacity or (0.55 if color in (GRAY, LGRAY) else 0.8)      # colored pipes keep their legend color
    return (f'<path d="M{x0:.1f},{a0:.1f} C{xm:.1f},{a0:.1f} {xm:.1f},{a1:.1f} {x1:.1f},{a1:.1f} L{x1:.1f},{b1:.1f} '
            f'C{xm:.1f},{b1:.1f} {xm:.1f},{b0:.1f} {x0:.1f},{b0:.1f} Z" fill="{color}" opacity="{opacity}"/>')


def flow_data() -> dict:
    reps = load("super_pac_reports")
    end = {c: max(r["coverage_end"] for r in reps if r["committee"] == c) for c in {r["committee"] for r in reps}}
    total = {c: sum(r["total_receipts"] for r in reps if r["committee"] == c) for c in end}
    recs = [r for r in load("super_pac_receipts") if r["committee"] in end and SINCE <= r["date"] <= end[r["committee"]]]
    org = lambda c, pat: [r for r in recs if r["committee"] == c and r["entity_type"] != "IND" and re.search(pat, r["contributor"].upper())]
    people = role_people()
    ffm, uj = "Fighting for Michigan PAC", "Unity & Justice Fund"
    in_window = lambda rs, c: [r for r in rs if r["committee"] == c and SINCE <= r["date"] <= end[c]]
    role_uj = [r for p in people.values() for r in in_window(p["pac"], uj)]
    role_ffm = {k: in_window(p["pac"], ffm) for k, p in people.items() if in_window(p["pac"], ffm)}
    top = max(role_ffm, key=lambda k: sum(r["amount"] for r in role_ffm[k]))
    camp = [(k, p) for k, p in people.items() if p["campaign"]]
    return {"end": end, "total": total, "people": people, "ffm": ffm, "uj": uj, "reports": reps,
            "cair_action": org(uj, r"^CAIR ACTION"), "role_uj": role_uj, "n_role_uj": len({k for k, p in people.items() if in_window(p["pac"], uj)}),
            "uj_to_ffm": org(ffm, r"^UNITY & JUSTICE FUND"), "imeu": org(ffm, r"MIDDLE EAST UNDERSTANDING"),
            "acmer": org(ffm, r"COMMITTEE FOR MIDDLE EAST RIGHTS"), "top_person": people[top], "top_rows": role_ffm[top],
            "other_role_ffm": [r for k, rs in role_ffm.items() if k != top for r in rs],
            "camp_people": camp, "camp_rows": [d for _, p in camp for d in p["campaign"]]}


def fig_flow(spending: bool) -> tuple[str, int]:
    f = flow_data()
    ffm, uj, total = f["ffm"], f["uj"], f["total"]
    amt = lambda rs: sum(r["amount"] or 0 for r in rs)
    rid = lambda rs: [receipt_id(r) for r in rs]
    rep_ids = lambda c: [f"P:{COMMITTEE_CODE[c]}:{r['file_number']}" for r in f["reports"] if r["committee"] == c]
    tp = f["top_person"]
    tp_role = next(iter(sorted(tp["orgs"])))
    named_ffm = amt(f["uj_to_ffm"]) + amt(f["imeu"]) + amt(f["top_rows"]) + amt(f["acmer"]) + amt(f["other_role_ffm"])
    pct = round(100 * named_ffm / total[ffm])
    sources = [  # (group, label, note, amount, rows, color)
        (uj, "CAIR Action", "CAIR's 501(c)(4) affiliate", amt(f["cair_action"]), rid(f["cair_action"]), BLUE),
        (uj, f"{f['n_role_uj']} people with documented roles", "in Muslim or Arab-advocacy groups", amt(f["role_uj"]), rid(f["role_uj"]), BLUE250),
        (uj, "All other donors to Unity & Justice", "", total[uj] - amt(f["cair_action"]) - amt(f["role_uj"]), rep_ids(uj), GRAY),
        (ffm, "IMEU Policy Project", "first filed as IMEU, Inc., a 501(c)(3) charity", amt(f["imeu"]), rid(f["imeu"]), PURPLE),
        (ffm, person(tp["name"]), f"{tp_role[0].replace('CAIR Michigan', 'CAIR-Michigan')} {tp_role[1].lower()}", amt(f["top_rows"]), rid(f["top_rows"]), BLUE250),
        (ffm, "ACMER", "American Committee for Middle East Rights", amt(f["acmer"]), rid(f["acmer"]), PURPLE),
    ]
    if f["other_role_ffm"]:
        sources.append((ffm, "Other people with documented roles", "", amt(f["other_role_ffm"]), rid(f["other_role_ffm"]), BLUE250))
    sources.append((ffm, "All other donors to Fighting for Michigan", "", total[ffm] - named_ffm, rep_ids(ffm), GRAY))
    scale = 900 / total[ffm]   # parameter: Fighting for Michigan's node is 900 px tall
    h = lambda v: max(2.0, v * scale)
    xs, xu, xf = 600, (1000 if spending else 1240), (1430 if spending else 1880)
    xe, nw = 1840, 22
    svg, ids = [], []
    # sources, stacked down the left with room for a two-line label each
    y, pos, group_prev = 150.0, [], uj      # room above for the Unity & Justice label
    for g, label, note, v, rows, col in sources:
        if g != group_prev:
            y += 40
            group_prev = g
        slot = max(h(v), 60)
        top = y + (slot - h(v)) / 2
        pos.append((top, top + h(v)))
        mid = top + h(v) / 2
        svg.append(f'<rect x="{xs - nw}" y="{top:.1f}" width="{nw}" height="{h(v):.1f}" fill="{col}"/>'
                   f'<text x="{xs - nw - 14}" y="{mid - 3:.1f}" font-size="20" font-weight="bold" fill="{INK}" text-anchor="end">{esc(label)}</text>'
                   f'<text x="{xs - nw - 14}" y="{mid + 21:.1f}" font-size="17" fill="{MUTED}" text-anchor="end">{esc(note + " · " if note else "")}{money(v)}</text>')
        y += slot + 8
    # Unity & Justice: level with its donors; Fighting for Michigan: lower, so the pipe from U&J falls into its top
    uj_top = pos[0][0]
    uj_h = h(total[uj])
    ffm_top = uj_top + uj_h + 60
    svg.append(f'<rect x="{xu}" y="{uj_top:.1f}" width="{nw}" height="{uj_h:.1f}" fill="{SLATE}"/>')
    svg.append(f'<rect x="{xf}" y="{ffm_top:.1f}" width="{nw}" height="{h(total[ffm]):.1f}" fill="{INK}"/>')
    cu, cf = uj_top, ffm_top
    for (g, label, note, v, rows, col), (a, b) in zip(sources, pos):
        if g == uj:
            svg.append(band(xs, a, b, xu, cu, cu + h(v), col))
            cu += h(v)
        else:
            continue
        ids += element("pipe", f"{label} to Unity & Justice", rows)
    v_uj = amt(f["uj_to_ffm"])
    svg.append(band(xu + nw, uj_top, uj_top + h(v_uj), xf, cf, cf + h(v_uj), SLATE))
    ids += element("pipe", "Unity & Justice to Fighting for Michigan", rid(f["uj_to_ffm"]))
    cf += h(v_uj)
    for (g, label, note, v, rows, col), (a, b) in zip(sources, pos):
        if g == ffm:
            svg.append(band(xs, a, b, xf, cf, cf + h(v), col))
            cf += h(v)
            ids += element("pipe", f"{label} to Fighting for Michigan", rows)
    ids += element("node", "Unity & Justice Fund", rep_ids(uj)) + element("node", "Fighting for Michigan PAC", rep_ids(ffm))
    share_ca = round(100 * amt(f["cair_action"]) / total[uj])
    ujl = [("Unity & Justice Fund (super PAC)", 20, INK, "bold"),
           (f"raised {money(total[uj])}, {date.fromisoformat(SINCE):%b %Y} to {date.fromisoformat(f['end'][uj]):%b %-d, %Y}", 17, MUTED, "normal"),
           (f"{share_ca}% from CAIR Action; its treasurer until 2025", 17, MUTED, "normal"),
           ("was CAIR Action's executive director", 17, MUTED, "normal"),
           (f"gave {money(v_uj)} to Fighting for Michigan", 17, MUTED, "normal")]
    for i, (t, fs, col, wt) in enumerate(ujl):      # above the node, where no pipe runs
        svg.append(f'<text x="{xu}" y="{uj_top - 118 + i * 23:.1f}" font-size="{fs}" font-weight="{wt}" fill="{col}">{esc(t)}</text>')
    lab_x, anchor = xf, "start"
    ffl = [("Fighting for Michigan PAC", 22, INK, "bold"), (f"raised {money(total[ffm])} through {date.fromisoformat(f['end'][ffm]):%b %-d, %Y}", 18, MUTED, "normal"),
           (f"{pct}% of it from the sources in color", 18, MUTED, "normal")]
    for i, (t, fs, col, wt) in enumerate(ffl):
        svg.append(f'<text x="{lab_x}" y="{ffm_top - 76 + i * 24:.1f}" font-size="{fs}" font-weight="{wt}" fill="{col}" text-anchor="{anchor}">{esc(t)}</text>')
    notes = ""
    if spending:
        sp = [s for s in load("super_pac_spending") if s["counts"]]
        regular = [s for s in sp if s["committee"] == ffm and s["form"] == "F3X"]
        es = [s for s in regular if s["support_oppose"] == "S" and "EL-SAYED" in (s["candidate"] or "")]
        st = [s for s in regular if s["support_oppose"] == "O" and "STEVENS" in (s["candidate"] or "")]
        assert len(es) + len(st) == len(regular), "a regular-report expenditure fits neither group"
        sid = lambda rs: [f"E:{COMMITTEE_CODE[s['committee']]}:{s['file_number']}:{s['transaction_id']}" for s in rs]
        fr = [r for r in f["reports"] if r["committee"] == ffm]
        op = sum(r["operating_expenditures"] for r in fr)
        oth = sum(r["other_disbursements"] + r["contributions_to_candidates_and_committees"] + r["contribution_refunds"]
                  + r["unexplained_disbursements"] for r in fr)
        cash = max(fr, key=lambda r: r["coverage_end"])["cash_on_hand_end"]
        outs = [("Ads and voter contact for El-Sayed", amt(es), sid(es), AQUA), ("Ads against Haley Stevens (D)", amt(st), sid(st), RED),
                ("Operating costs", op, rep_ids(ffm), GRAY), ("Other spending", oth, rep_ids(ffm), GRAY),
                (f"Cash on hand, {date.fromisoformat(f['end'][ffm]):%b %-d}", cash, rep_ids(ffm), LGRAY)]
        assert abs(sum(o[1] for o in outs) - total[ffm] - fr[0]["cash_on_hand_beginning"]) < 1, "spending column does not balance"
        co, ye = ffm_top, ffm_top
        for label, v, rows, col in outs:
            slot = max(h(v), 56)
            top = ye + (slot - h(v)) / 2
            svg.append(band(xf + nw, co, co + h(v), xe, top, top + h(v), col)
                       + f'<rect x="{xe}" y="{top:.1f}" width="{nw}" height="{h(v):.1f}" fill="{col}"/>'
                       f'<text x="{xe + nw + 14}" y="{top + h(v) / 2 - 3:.1f}" font-size="20" font-weight="bold" fill="{INK}">{esc(label)}</text>'
                       f'<text x="{xe + nw + 14}" y="{top + h(v) / 2 + 21:.1f}" font-size="18" fill="{MUTED}">{money(v)}</text>')
            ids += element("spending", label, rows)
            co += h(v)
            ye += slot + 34
        bottom = ye
        # what the notices filed since the last regular report add (not drawn: the receipts that paid for them are not yet filed)
        late = [s for s in sp if s["form"] == "F24"]
        late_f = [s for s in late if s["committee"] == ffm]
        late_u = [s for s in late if s["committee"] == uj and "EL-SAYED" in (s["candidate"] or "")]
        big = max(late_u, key=lambda s: s["amount"])
        pro_rogers = [s for s in late_f if s["support_oppose"] == "S" and "ROGERS" in (s["candidate"] or "")]
        ids += element("footnote figure", "notices since the last regular report", sid(late_f + late_u))
        notes = (f" <b>Since {date.fromisoformat(f['end'][ffm]):%b %-d} (not drawn):</b> 48-hour notices report {money(amt(late_f))} more by Fighting for "
                 f"Michigan ({money(amt([s for s in late_f if s['support_oppose'] == 'S' and 'EL-SAYED' in (s['candidate'] or '')]))} for El-Sayed, "
                 f"{money(amt([s for s in late_f if s['support_oppose'] == 'O' and 'ROGERS' in (s['candidate'] or '')]))} against Republican Mike Rogers"
                 + (f", and {money(amt(pro_rogers))} in mail filed as supporting Rogers" if pro_rogers else "")
                 + f") and {money(amt(late_u))} by Unity &amp; Justice for El-Sayed, including a {money(big['amount'])} canvassing estimate dated "
                 f"{date.fromisoformat(big['expenditure_date']):%b %-d}, when its last report showed {money(max((r for r in f['reports'] if r['committee'] == uj), key=lambda r: r['coverage_end'])['cash_on_hand_end'])} on hand. "
                 "The receipts that paid for them are due Oct 20. Ads for El-Sayed and against Stevens are the split each ad was filed under; "
                 "\"other spending\" is mostly gifts to a nonprofit, 5PLUS1.")
    # the campaign itself, on its own scale
    cy = max(y, ffm_top + h(total[ffm]), bottom if spending else 0) + 50
    camp_net = sum(d["net"] for d in f["camp_rows"])
    all_net = sum(json.loads(l)["net"] for l in open(ROOT / "analysis" / "donors_net.jsonl", encoding="utf-8"))
    n_all = sum(1 for _ in open(ROOT / "analysis" / "donors_net.jsonl", encoding="utf-8"))
    bw = W - 120 - 600
    wr = bw * camp_net / all_net
    svg.append(f'<text x="0" y="{cy + 26:.1f}" font-size="22" font-weight="bold" fill="{INK}">The campaign itself</text>'
               f'<text x="0" y="{cy + 52:.1f}" font-size="17" fill="{MUTED}">different scale: the whole bar is {money(all_net)}</text>'
               f'<rect x="600" y="{cy + 8:.1f}" width="{bw}" height="40" fill="{GRAY}"/>'
               f'<rect x="600" y="{cy + 8:.1f}" width="{max(wr, 3):.1f}" height="40" fill="{BLUE250}"/>'
               f'<text x="600" y="{cy + 76:.1f}" font-size="18" fill="{INK}">{len(f["camp_people"])} people with documented roles gave '
               f'{money(camp_net)} net, {100 * camp_net / all_net:.1f}% of what individual donors gave the campaign through Sep 30</text>')
    ids += element("campaign bar", "role-holders to the campaign", [donor_id(d) for d in f["camp_rows"]])
    ids += element("campaign bar", "all individual donors", [f"ALL:donors_net:{n_all}"])
    h_svg = cy + 100
    svg = [f'<svg width="{W - 120}" height="{h_svg:.0f}" viewBox="0 0 {W - 120} {h_svg:.0f}">'] + svg + ["</svg>"]
    who = "a CAIR-Michigan director, two Arab and Palestinian advocacy groups and a super PAC CAIR Action helps fund"
    if spending:
        title = (f"{pct}% of the pro-El-Sayed super PAC's money came from {who}; by {date.fromisoformat(f['end'][ffm]):%b %-d} it had spent "
                 f"{money(amt(es))} for him and {money(amt(st))} against Haley Stevens")
    else:
        title = f"{pct}% of the pro-El-Sayed super PAC's money came from {who}"
    doc = shell(
        title, "Where the super PAC money came from" + (", and where it went" if spending else ""),
        "Pipe widths are in proportion to dollars. Receipts as Fighting for Michigan PAC and Unity &amp; Justice Fund filed them, "
        f"{date.fromisoformat(SINCE):%B %Y} through {date.fromisoformat(f['end'][ffm]):%B %-d, %Y}; Unity &amp; Justice's gift to Fighting "
        "for Michigan is drawn from Unity &amp; Justice, which pooled it with its other money.",
        legend([(BLUE, "Muslim organization"), (PURPLE, "Arab or Palestinian advocacy group"), (BLUE250, "people with documented roles in such groups"),
                (SLATE, "super PAC CAIR Action helps fund"), (GRAY, "all other donors")]) + "\n".join(svg) + cite(ids),
        "<b>Source:</b> FEC reports of Fighting for Michigan PAC, Unity &amp; Justice Fund and Abdul for U.S. Senate, as amended through Oct 17, "
        "2026 (on Oct 17 Fighting for Michigan refiled IMEU's two gifts, same address, under the name \"The Institute for Middle East "
        "Understanding (IMEU) Policy Project\", citing \"a data entry error\"). Roles are from the organizations' own filings and pages, each "
        "confirmed on two attributes. Unity &amp; Justice's treasurer is from its own FEC reports; CAIR Action's description of itself and "
        f"of its executive director is from its own pages. {esc(person(tp['name']))} is widely reported to be El-Sayed's father-in-law; "
        "we found no primary record of it, so the figure does not say so. <b>Not traceable:</b> money is pooled, so no donor's dollars can be "
        "followed to a particular ad." + notes,
        W, int(h_svg) + (520 if spending else 400))
    return doc, int(h_svg) + (520 if spending else 400)


# ---- figure 6: who gave the most -----------------------------------------------------------------------------------
LIMIT = 7000   # parameter: the most one person may give, primary and general together


def fig_constituency() -> tuple[str, int]:
    tiers = json.loads((ROOT / "analysis" / "name_origin_share.json").read_text(encoding="utf-8"))["by_donor_tier"]
    donors = [json.loads(l) for l in open(ROOT / "analysis" / "donors_net.jsonl", encoding="utf-8")]
    top = [d for d in donors if d["net"] >= LIMIT - 0.005]          # the same cut as scripts/name_origin_share.py
    a, m = tiers["all_donors"], tiers["at_7000_max"]
    assert a["n_donors"] == len(donors) and m["n_donors"] == len(top), "name_origin_share.json is out of date"
    over = sum(d["net"] > LIMIT + 0.01 for d in top)
    cell, gap = 54, 8
    panels = [(0, f"All {len(donors):,} donors to the campaign", a, [f"ALL:donors_net:{len(donors)}"]),
              (1180, f"The {len(top):,} who gave {money(LIMIT)}, the maximum", m, [donor_id(d) for d in top])]
    h_svg = 60 + 10 * (cell + gap) + 30
    svg, ids = [f'<svg width="{W - 120}" height="{h_svg}" viewBox="0 0 {W - 120} {h_svg}">'], []
    for x0, label, t, rows in panels:
        k = round(t["expected_pct_of_donors"])
        svg.append(f'<text x="{x0}" y="30" font-size="26" font-weight="bold" fill="{INK}">{esc(label)}</text>')
        for i in range(100):
            r, c = divmod(i, 10)
            svg.append(f'<rect x="{x0 + c * (cell + gap)}" y="{60 + r * (cell + gap)}" width="{cell}" height="{cell}" rx="4" '
                       f'fill="{BLUE if i < k else LGRAY}"/>')
        tx = x0 + 10 * (cell + gap) + 30
        svg.append(f'<text x="{tx}" y="{60 + 150}" font-size="128" font-weight="bold" fill="{BLUE}">{k}%</text>'
                   f'<text x="{tx}" y="{60 + 200}" font-size="24" fill="{INK}">of these donors have</text>'
                   f'<text x="{tx}" y="{60 + 230}" font-size="24" fill="{INK}">Arab- or Muslim-heritage names</text>'
                   f'<text x="{tx}" y="{60 + 290}" font-size="22" fill="{MUTED}">They gave {round(t["expected_pct_of_net_dollars"])}% of</text>'
                   f'<text x="{tx}" y="{60 + 318}" font-size="22" fill="{MUTED}">the group\'s dollars</text>')
        ids += element("waffle", label, rows)
    svg.append("</svg>")
    doc = shell(
        f"{round(m['expected_pct_of_donors'])}% of the donors who gave El-Sayed's campaign the {money(LIMIT)} maximum have Arab- or "
        "Muslim-heritage names",
        "Who gave the most",
        "Each square is 1% of donors. The measure is a name's heritage, not anyone's religion: Arab Christians count, and Muslims "
        "whose names come from other traditions do not.",
        legend([(BLUE, "Arab- or Muslim-heritage name"), (LGRAY, "other names")]) + "\n".join(svg) + cite(ids),
        "<b>Source:</b> FEC filings of Abdul for U.S. Senate, itemized gifts from individuals including those passed through its joint "
        "fundraising committees, net of refunds and reattributions, through Sep 30, 2026; a donor is one name at one ZIP code. "
        f"{over} of the {len(top)} are above {money(LIMIT)} net, pending refunds. <b>Method:</b> each name's chance of being Arab- or "
        "Muslim-heritage, from a name-origin lexicon checked against a Wikipedia name-category gold set, summed over donors: "
        f"{m['expected_pct_of_donors']}% for the maximum donors (range {m['low_pct_of_donors']}–{m['high_pct_of_donors']}%), "
        f"{a['expected_pct_of_donors']}% for all donors (range {a['low_pct_of_donors']}–{a['high_pct_of_donors']}%). The low end counts the "
        "likelier of the two names, the high end either. <b>Not shown:</b> any individual's label; the estimate is for groups only.",
        W, h_svg + 340)
    return doc, h_svg + 340


FIGS = {"e1-money-from-muslim-and-arab-advocacy-roles": fig_islam_money, "e1b-cair-money-counted-two-ways": fig_two_counts,
        "e2-jukaku-money-in-the-coverage": fig_jukaku,
        "e3-what-held-up": fig_verdicts, "e4-cair-donor-figure": fig_cair,
        "e5-super-pac-money-flow": lambda: fig_flow(False), "e5b-super-pac-money-flow-and-spending": lambda: fig_flow(True),
        "e6-max-donors-heritage-names": fig_constituency, "e7-donors-and-groups": fig_combo}
WIDTH = {"e7-donors-and-groups": WC}

if __name__ == "__main__":
    if "--list-elements" in sys.argv:
        for f in FIGS.values():
            f()
        print(json.dumps(ELEMENTS))
    else:
        for stem in [a for a in sys.argv[1:] if not a.startswith("-")] or list(FIGS):
            doc, height = FIGS[stem]()
            render(stem, doc, WIDTH.get(stem, W), height)
