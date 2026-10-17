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
from fig_common import (AQUA, AXIS, BLUE, GRAY, GRID, INK, LGRAY, MUTED, ORANGE, PURPLE, RED, YELLOW, cite, esc,  # noqa: E402
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


# ---- figure 1: big super PAC donors, named or not ---------------------------------------------------------------
def fig_donors_named() -> tuple[str, int]:
    threshold = 50 * 1000  # parameter: contributors at or above this total to one PAC
    recs = [r for r in load("super_pac_receipts") if r["committee"] in ("Fighting for Michigan PAC", "Unity & Justice Fund")]
    agg = defaultdict(lambda: {"amount": 0.0, "n": 0, "rows": [], "city": "", "state": "", "kind": ""})
    for r in recs:
        k = (r["committee"], " ".join(r["contributor"].upper().replace(",", ", ").split()), r["entity_type"])
        a = agg[k]
        a["amount"] += r["amount"] or 0
        a["n"] = max(a["n"], r["n_stories_naming_contributor"])
        a["rows"].append(receipt_id(r))
        a.update(city=r["city"] or "", state=r["state"] or "", kind=r["entity_type"])
    big = [(k, v) for k, v in agg.items() if v["amount"] >= threshold]
    named = sorted([x for x in big if x[1]["n"] > 0], key=lambda x: -x[1]["amount"])
    unnamed = sorted([x for x in big if x[1]["n"] == 0], key=lambda x: -x[1]["amount"])
    top = max(v["amount"] for _, v in big)
    n_stories = len(load("stories"))
    row_h, top_y, panel_w, label_w = 50, 70, 1100, 470
    rows = max(len(named), len(unnamed))
    h_svg = top_y + rows * row_h + 20
    svg, ids = [f'<svg width="{W - 120}" height="{h_svg}" viewBox="0 0 {W - 120} {h_svg}">'], []
    for p, (title, items, color) in enumerate((("Named in at least one story", named, BLUE),
                                               ("Named in none of the stories", unnamed, ORANGE))):
        x0 = p * (panel_w + 80)
        svg.append(f'<text x="{x0}" y="34" font-size="26" font-weight="bold" fill="{INK}">{esc(title)} ({len(items)})</text>')
        for i, ((committee, contributor, kind), v) in enumerate(items):
            y = top_y + i * row_h
            label = person(contributor) if kind == "IND" else short_org(contributor)
            tag = "FFM" if committee.startswith("Fighting") else "U&J"
            bar = (panel_w - label_w - 230) * v["amount"] / top
            svg.append(f'<text x="{x0}" y="{y + 22}" font-size="19" fill="{INK}">{esc(label[:44])}</text>'
                       f'<text x="{x0}" y="{y + 42}" font-size="14" fill="{MUTED}">{esc(tag)} · {esc(v["city"].title())}, {esc(v["state"])}</text>'
                       f'<rect x="{x0 + label_w}" y="{y + 8}" width="{bar:.1f}" height="28" rx="3" fill="{color}" opacity="0.85"/>'
                       f'<text x="{x0 + label_w + bar + 10:.1f}" y="{y + 29}" font-size="18" font-weight="bold" fill="{INK}">{money(v["amount"])}</text>')
            if v["n"]:
                svg.append(f'<text x="{x0 + panel_w - 20}" y="{y + 29}" font-size="16" fill="{MUTED}" text-anchor="end">'
                           f'{v["n"]} {"story" if v["n"] == 1 else "stories"}</text>')
            ids += element("bar", f"{committee}: {contributor}", v["rows"])
    svg.append("</svg>")
    total_un = sum(v["amount"] for _, v in unnamed)
    doc = shell(
        f"{len(unnamed)} of the {len(big)} largest donors to the pro-El-Sayed super PACs appear in no story",
        "Who funded Fighting for Michigan and Unity & Justice",
        f"Every contributor who gave {money(threshold)} or more to either PAC, by total given. Left: named in at least one of "
        f"the {n_stories:,} stories captured; right: never named. The unnamed group gave {money(total_un)}.",
        legend([(BLUE, "named in at least one story"), (ORANGE, "named in none"), (GRAY, "FFM = Fighting for Michigan PAC, U&J = Unity & Justice Fund")])
        + "\n".join(svg) + cite(ids),
        "<b>Source:</b> the PACs' FEC receipts (OpenFEC e-file and processed data, reports through Aug 31, 2026, as amended "
        "through Oct 17, 2026). <b>Named</b> means the contributor's first and last name, side by side, or the organization's "
        "name appears in a captured story; a donor reported under a nickname or another name form counts as unnamed. A contributor "
        "filed under two names or two cities is shown twice; the Unity &amp; Justice gift under Tayeb Jukaku's name, filed from "
        "Tracy, CA, is not confirmed as his. IMEU Policy Project is the donor name the PAC's Oct 17 amendments give for gifts first "
        "reported from the Institute for Middle East Understanding, Inc. <b>Not shown:</b> smaller contributors, and American "
        "Priorities, which also spent for El-Sayed but backs other candidates.",
        W, h_svg + 400)
    return doc, h_svg + 400


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


FIGS = {"e1-super-pac-donors-named": fig_donors_named, "e2-jukaku-money-in-the-coverage": fig_jukaku,
        "e3-what-held-up": fig_verdicts, "e4-cair-donor-figure": fig_cair}

if __name__ == "__main__":
    if "--list-elements" in sys.argv:
        for f in FIGS.values():
            f()
        print(json.dumps(ELEMENTS))
    else:
        for stem in [a for a in sys.argv[1:] if not a.startswith("-")] or list(FIGS):
            doc, height = FIGS[stem]()
            render(stem, doc, W, height)
