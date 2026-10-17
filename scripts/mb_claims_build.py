"""Merge extracted article claims into structured tables and match named people and groups to FEC records.

Usage: python scripts/mb_claims_build.py <mb_claims_dir> <out_dir>
  <mb_claims_dir>: raw_dl/ (archived article html/txt/json, one per captured URL), extract_v2/*/ and
      extract_v3/*/claims.jsonl (claims extracted from each relevant article), screen.jsonl (from mb_claims_screen.py)
  <out_dir>: stories, claims, links, entities, ties, fec_rows, super_pac_receipts as .jsonl + .csv

Other inputs
  analysis/private/mb_subject_map.json  how each subject as written resolves to one or more entities (curated)
  analysis/private/mb_verdicts.jsonl    optional; one verdict per tie_id, with primary evidence (curated)
  analysis/private/mb_corrections.jsonl optional; story-level field fixes, each with a reason
  analysis/donors_net.jsonl             campaign donors, net, through Sep 30, 2026
  <mb_claims_dir>/../openfec_pacs_dl/rows/*.json  super PAC and MERIT PAC schedule A rows from OpenFEC

Name matching is a candidate list (last + first token), never an identity finding; each match carries
the FEC record's city, state, occupation and employer so a reviewer can confirm or reject it.
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MB, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
PRIVATE = ROOT / "analysis" / "private"
SMAP = json.loads((PRIVATE / "mb_subject_map.json").read_text(encoding="utf-8"))
VERDICTS = PRIVATE / "mb_verdicts.jsonl"
CORRECTIONS = PRIVATE / "mb_corrections.jsonl"   # story-level field fixes, each with a written reason
DONATION = ("donated_to_campaign", "donated_to_super_pac")


def norm_name(s: str) -> tuple[str, str]:
    """('LAST', 'FIRST') from 'First Last', 'Last, First' or 'Dr. First M. Last'."""
    s = re.sub(r"\b(Dr|Mr|Mrs|Ms|Sen|Rep|Imam|Sheikh|Prof)\.?\s+", "", s or "", flags=re.I)
    s = re.sub(r"\([^)]*\)", "", s).strip()
    if "," in s:
        last, first = s.split(",", 1)
    else:
        parts = s.split()
        if len(parts) < 2:
            return (re.sub(r"[^A-Z]", "", s.upper()), "")
        first, last = parts[0], parts[-1]
    t = lambda x: re.sub(r"[^A-Z]", "", x.upper())
    return t(last), t(first.split()[0] if first.split() else "")


def org_key(s: str) -> str:
    return re.sub(r"\b(INC|LLC|THE)\b|[^A-Z0-9&]", "", (s or "").upper())


COUNTERPARTY = [(r"\bCAIR\b|Council on American.Islamic", "CAIR"),
                (r"\bISNA\b|Islamic Society of North America", "ISNA"),
                (r"\bIARA\b|Islamic American Relief", "IARA"),
                (r"Holy Land", "Holy Land Foundation"),
                (r"Freedom and Justice", "Freedom and Justice Party (Muslim Brotherhood, Egypt)"),
                (r"Brotherhood|Ikhwan", "Muslim Brotherhood"),
                (r"Islamic Association for Palestine|\bIAP\b", "Islamic Association for Palestine"),
                (r"American Muslims for Palestine|\bAMP\b|AJP", "AMP / AJP Action"),
                (r"Life for Relief|\bLIFE\b", "Life for Relief and Development"),
                (r"\bACMER\b|Middle East Rights", "ACMER"),
                (r"Institute for Middle East Understanding|\bIMEU\b", "IMEU"),
                (r"Unity (&|and) Justice", "Unity & Justice Fund"),
                (r"Hamas", "Hamas"), (r"Hezbollah", "Hezbollah"),
                (r"Khamenei|Iran", "Iran / Iranian regime"),
                (r"Muslim Students? Association|\bMSA\b", "Muslim Students Association"),
                (r"al.?Qa.?ida|bin Laden", "al-Qaeda"),
                (r"watch ?list", "federal terrorism watchlist"),
                (r"World Trade Center", "1993 World Trade Center bombing"),
                (r"terror|jihad|extremis|Islamist", "terrorism / extremism (generic)")]

RECIPIENT = [(r"Fighting for Michigan", "Fighting for Michigan PAC"),
             (r"Unity (&|and) Justice", "Unity & Justice Fund"),
             (r"American Priorities", "American Priorities"),
             (r"2018|governor", "El-Sayed 2018 governor campaign"),
             (r"super ?PAC|\bPAC\b", "unnamed super PAC supporting El-Sayed"),
             (r"Abdul for U\.S\. Senate|campaign", "Abdul for U.S. Senate")]


def norm_counterparty(s: str | None) -> str:
    for pat, name in COUNTERPARTY:
        if s and re.search(pat, s, re.I):
            return name
    return (s or "none stated").strip()


def norm_recipient(s: str | None) -> str:
    for pat, name in RECIPIENT:
        if s and re.search(pat, s, re.I):
            return name
    return "unspecified"


def link_kind(u: str) -> str:
    h = urlsplit(u).netloc.lower()
    if "fec.gov" in h:
        return "fec_filing"
    if any(x in h for x in ("courtlistener", "uscourts", "pacer", "investigativeproject.org/case_docs")):
        return "court_record"
    if h.endswith(".gov") or h.endswith(".gov.uk") or "justice.gov" in h or "state.gov" in h or "treasury.gov" in h:
        return "government"
    if any(x in h for x in ("x.com", "twitter.com", "facebook.com", "instagram.com", "youtube.com", "youtu.be", "tiktok.com", "rumble.com", "t.me")):
        return "social_or_video"
    if "web.archive.org" in h or "archive.ph" in h or "archive.is" in h or "archive.today" in h:
        return "archive"
    if "propublica.org" in h and "nonprofits" in u or "irs.gov" in h:
        return "tax_filing"
    return "news_or_other"


def tie_id(entity: str, link_type: str, counterparty: str) -> str:
    return hashlib.sha1(f"{entity}|{link_type}|{counterparty}".encode()).hexdigest()[:12]


# ---- stories: every captured URL, extracted or not ----------------------------------------------
meta = {Path(f).stem: json.load(open(f)) for f in glob.glob(str(MB / "raw_dl" / "*.json"))}
screen = {r["h"]: r["screen"] for r in map(json.loads, open(MB / "screen.jsonl"))} if (MB / "screen.jsonl").exists() else {}
extracted = {}
for f in sorted(glob.glob(str(MB / "extract_v2" / "*" / "claims.jsonl")) + glob.glob(str(MB / "extract_v3" / "*" / "claims.jsonl"))):
    for line in open(f, encoding="utf-8"):
        if line.strip():
            a = json.loads(line)
            extracted[a["h"]] = a

# how each URL was found (the discovery lists kept in the corpus folder)
DISCOVERY = [("urls_round1.txt", "search round 1"), ("corpus_candidates.txt", "search round 1 candidates"),
             ("evidence_urls.txt", "link cited by a captured story (round 1)"),
             ("snowball_round2_curl.txt", "link inside a captured story (round 2)"),
             ("search_round3_urls.txt", "search round 3")]
found_via = defaultdict(list)
for fname, label in DISCOVERY:
    if (MB / fname).exists():
        for u in open(MB / fname, encoding="utf-8"):
            if u.strip():
                found_via[u.strip()].append(label)
if (MB / "search_round3.tsv").exists():
    for row in csv.DictReader(open(MB / "search_round3.tsv", encoding="utf-8"), delimiter="\t"):
        if row.get("url"):
            found_via[row["url"].strip()].append(f"query: {row.get('query')}")

stories, claims, links = [], [], []
for h, m in sorted(meta.items(), key=lambda kv: kv[1]["url"]):
    a = extracted.get(h)
    if a:
        disposition = "extracted_in_scope" if a.get("in_scope") else "extracted_out_of_scope"
    elif m.get("status") == "ok":
        disposition = {"to_extract": "awaiting_extraction", "out_no_el_sayed": "screened_out_no_el_sayed",
                       "out_no_theme_keyword": "screened_out_no_theme_keyword"}.get(screen.get(h), "awaiting_screen")
    else:
        disposition = f"not_captured_{m.get('status')}" + ("_wayback_tried" if m.get("wayback_tried") else "")
    stories.append({
        "story_id": h, "url": m["url"], "final_url": m.get("final_url"),
        "outlet": (a or {}).get("outlet") or m.get("site") or urlsplit(m["url"]).netloc.removeprefix("www."),
        "outlet_kind": (a or {}).get("outlet_kind"), "published": (a or {}).get("published") or (m.get("published") or "")[:10] or None,
        "author": (a or {}).get("author") or m.get("author"), "headline": (a or {}).get("headline") or m.get("headline"),
        "disposition": disposition, "found_via": "; ".join(dict.fromkeys(found_via.get(m["url"], []))) or "unrecorded",
        "in_scope": (a or {}).get("in_scope"), "scope_reason": (a or {}).get("scope_reason"),
        "is_original_reporting": (a or {}).get("is_original_reporting"), "relies_on": "; ".join((a or {}).get("relies_on") or []),
        "campaign_response_quoted": (a or {}).get("campaign_response_quoted"), "n_claims": len((a or {}).get("claims") or []),
        "n_links": len(m.get("links", [])), "capture_status": m.get("status"), "http_code": m.get("http_code"),
        "archived_sha256": m.get("sha256"), "fetched_utc": m.get("fetched_utc"),
        "wayback_snapshot": m.get("wayback_snapshot"), "text_chars": m.get("text_chars"),
    })
    cited = set()
    for c in ((a or {}).get("claims") or []) if (a or {}).get("in_scope") else []:
        ev = c.get("evidence_cited") or []
        cited |= {e["url"] for e in ev if e.get("url")}
        claims.append({
            "claim_id": f"{h}-{c.get('n')}", "story_id": h, "outlet": a.get("outlet"),
            "published": a.get("published"), "url": a["url"],
            **{k: c.get(k) for k in ("subject", "subject_type", "subject_role", "link_type", "counterparty",
                                      "counterparty_characterization", "amount_usd", "date_stated", "recipient", "quote")},
            "counterparty_norm": norm_counterparty(c.get("counterparty")),
            "recipient_norm": norm_recipient(c.get("recipient")) if c.get("link_type") in DONATION else None,
            "evidence_urls": " | ".join(e["url"] for e in ev if e.get("url")),
            "evidence_unlinked": " | ".join(e.get("anchor") or "" for e in ev if not e.get("url")),
        })
    for i, l in enumerate(m.get("links", [])):
        links.append({"story_id": h, "link_n": i + 1, "story_disposition": disposition, "outlet": stories[-1]["outlet"],
                      "anchor": l["anchor"], "url": l["url"], "link_kind": link_kind(l["url"]),
                      "cited_for_a_claim": l["url"] in cited})

if CORRECTIONS.exists():
    by_id = {s["story_id"]: s for s in stories}
    for line in CORRECTIONS.open(encoding="utf-8"):
        if line.strip():
            fix = json.loads(line)
            by_id[fix["story_id"]][fix["field"]] = fix["value"]
            by_id[fix["story_id"]]["corrections"] = (by_id[fix["story_id"]].get("corrections") or "") + fix["reason"]

# ---- entities: resolve subjects, then FEC candidate matches -------------------------------------
donors = [json.loads(l) for l in open(ROOT / "analysis" / "donors_net.jsonl", encoding="utf-8")]
by_name = defaultdict(list)
for d in donors:
    by_name[(d["last_norm"].replace(" ", ""), d["first_norm"].split(" ")[0] if d["first_norm"] else "")].append(d)

COMMITTEE = {"ffm_A": "Fighting for Michigan PAC", "unity_A": "Unity & Justice Fund", "merit_A": "ACMER MERIT PAC",
             "cairaction_A": "CAIR Action PAC", "amprio_A": "American Priorities"}
pac_by_person, pac_by_org, pac_all = defaultdict(list), defaultdict(list), []
for f in sorted(glob.glob(str(MB.parent / "openfec_pacs_dl" / "rows" / "*_A.json"))):
    j = json.load(open(f))
    committee = COMMITTEE[Path(f).stem]
    # raw e-file rows from the latest version of each report first, then processed rows not already seen
    rows = [r for r in j["efile"] if not (r.get("filing") or {}).get("amended_by")] + j["processed"]
    seen = set()
    for r in rows:
        tid = r.get("transaction_id")
        if tid in seen or r.get("memo_code") == "X":
            continue
        seen.add(tid)
        row = {"committee": committee, "date": (r.get("contribution_receipt_date") or "")[:10],
               "amount": r.get("contribution_receipt_amount"), "contributor": (r.get("contributor_name") or "").rstrip(", "),
               "city": r.get("contributor_city"), "state": r.get("contributor_state"),
               "occupation": r.get("contributor_occupation"), "employer": r.get("contributor_employer"),
               "file_number": r.get("file_number"), "transaction_id": tid, "entity_type": r.get("entity_type"),
               "aggregate_ytd": r.get("contributor_aggregate_ytd")}
        pac_all.append(row)
        if r.get("entity_type") == "IND":
            pac_by_person[norm_name(r.get("contributor_name") or "")].append(row)
        else:
            pac_by_org[org_key(r.get("contributor_name"))].append(row)

alias = {k: tuple(v.split("|")) for k, v in SMAP["fec_aliases"].items()}


def fec_key(name: str) -> tuple[tuple[str, str], str]:
    """The FEC (last, first) key for a person as named in articles, and how it was found."""
    if name in alias:
        return alias[name], "alias"
    key = norm_name(name)
    if key in by_name or key in pac_by_person:
        return key, "as_written"
    sw = (key[1], key[0])
    if sw in by_name or sw in pac_by_person:
        return sw, "name_order_swapped"
    return key, "no_fec_match"


def resolve(subject: str) -> tuple[list[str], str]:
    r = SMAP["subjects"].get(subject)
    return (r["canonical"], r["kind"]) if r else ([subject], "unmapped")


entities: dict[str, dict] = {}
claim_entities = []                     # (claim, entity) pairs; a claim naming several people counts for each
for c in claims:
    names, kind = resolve(c["subject"])
    c["entities"] = "; ".join(names)
    c["entity_kind"] = kind
    for n in names:
        e = entities.setdefault(n, {"entity": n, "kind": kind, "names_as_written": set(), "claim_ids": [], "stories": set(),
                                    "outlets": set(), "subject_types": set()})
        e["names_as_written"].add(c["subject"]); e["claim_ids"].append(c["claim_id"]); e["stories"].add(c["story_id"])
        e["outlets"].add(c["outlet"]); e["subject_types"].add(c["subject_type"])
        claim_entities.append((c, n))

ent_rows = []
for n, e in entities.items():
    camp, pac, how = [], [], ""
    if e["kind"] == "person":
        key, how = fec_key(n)
        camp, pac = by_name.get(key, []), pac_by_person.get(key, [])
    elif e["kind"] == "organization":
        filed = SMAP["org_fec_names"].get(n, n)
        pac = [p for k, ps in pac_by_org.items() if k.startswith(org_key(filed)) for p in ps]
        how = "org_name" if pac else "no_fec_match"
    e["fec_match_how"] = how
    e["campaign"] = camp
    e["pac"] = sorted(pac, key=lambda p: p["date"])
    ent_rows.append({
        "entity": n, "kind": e["kind"], "names_as_written": "; ".join(sorted(e["names_as_written"])),
        "subject_types": "; ".join(sorted(e["subject_types"])), "n_claims": len(e["claim_ids"]), "n_stories": len(e["stories"]),
        "n_outlets": len(e["outlets"]), "fec_match_how": how, "campaign_fec_candidates": len(camp),
        "campaign_net_total": round(sum(d["net"] for d in camp), 2) if camp else None,
        "campaign_fec": " || ".join(f"{d['name']} | {d['city']}, {d['state']} | {d['occupation']} / {d['employer']} | net ${d['net']:,.2f}"
                                    f" (direct ${d['gross']:,.2f}, joint cmte ${d['joint_committee']:,.2f}, refunded ${d['refunded']:,.2f}"
                                    f"{', at $7,000 max' if d['net'] >= 6999.995 else ''})" for d in camp),
        "super_pac_total": round(sum(p["amount"] or 0 for p in pac), 2) if pac else None,
        "super_pac_fec": " || ".join(f"{p['committee']} {p['date']} ${p['amount']:,.0f} | {p['contributor']} | {p['city']}, {p['state']}"
                                     f" | {p['occupation']} / {p['employer']} | FEC file {p['file_number']}" for p in e["pac"]),
        "claim_ids": " ".join(e["claim_ids"]),
    })
ent_rows.sort(key=lambda r: -r["n_claims"])

# ---- every FEC row behind each named person or group: campaign gifts, reattributions, joint-committee shares,
# refunds (by the same donor key the net totals use), and super PAC receipts ----------------------------------
sys.path.insert(0, str(ROOT / "scripts"))
from top_donors import (AMT, CITY, DATE, EMP, ENTITY, FIRST, LAST, OCC, STATE, STREET1, SUFFIX, TRAN, ZIP,  # noqa: E402
                        key_of, load_filings)

REPORT = {re.search(r"(\d{7})\.csv$", p.name).group(1): p.stem.rsplit("_", 1)[0]
          for p in (ROOT / "data" / "filings").glob("*.csv")}
dkey = lambda d: (d["last_norm"], d["first_norm"], d["suffix"], d["zip5"], d["house"])
wanted = {dkey(d): n for n, e in entities.items() for d in e.get("campaign", [])}
sa, memo, jfc, refunds = load_filings()
fec_rows = []
for kind, rows in (("gift", [(k[0], r) for k, r in sa.items()]), ("reattribution", memo), ("joint_committee_share", jfc),
                   ("refund", refunds)):
    for num, r in rows:
        if r[ENTITY] != "IND":
            continue
        n = wanted.get(key_of(r[LAST], r[FIRST], r[SUFFIX], r[ZIP], r[STREET1]))
        if n:
            amt = float(r[AMT] or 0)
            fec_rows.append({"entity": n, "committee": "Abdul for U.S. Senate", "kind": kind, "date": f"{r[DATE][:4]}-{r[DATE][4:6]}-{r[DATE][6:]}",
                             "amount": -amt if kind == "refund" else amt, "name_as_filed": f"{r[LAST]}, {r[FIRST]}",
                             "city": r[CITY], "state": r[STATE], "occupation": r[OCC], "employer": r[EMP],
                             "report": REPORT.get(num), "fec_file_number": num, "transaction_id": r[TRAN]})
for n, e in entities.items():
    for p in e.get("pac", []):
        fec_rows.append({"entity": n, "committee": p["committee"], "kind": "super_pac_receipt", "date": p["date"],
                         "amount": p["amount"], "name_as_filed": p["contributor"], "city": p["city"], "state": p["state"],
                         "occupation": p["occupation"], "employer": p["employer"], "report": None,
                         "fec_file_number": p["file_number"], "transaction_id": p["transaction_id"]})
fec_rows.sort(key=lambda r: (r["entity"], r["committee"], r["date"]))

# ---- every receipt of the super PACs backing El-Sayed, with the stories (if any) that name the contributor ----
texts = {Path(t).stem: open(t, encoding="utf-8", errors="replace").read() for t in glob.glob(str(MB / "raw_dl" / "*.txt"))}
lower = {h: t.lower() for h, t in texts.items()}
_named: dict = {}


def stories_naming(row: dict) -> list[str]:
    key = (row["entity_type"], row["contributor"].upper())
    if key not in _named:
        _named[key] = _stories_naming(row)
    return _named[key]


def _stories_naming(row: dict) -> list[str]:
    if row["entity_type"] == "IND":
        last, first = norm_name(row["contributor"])
        if not last or not first:
            return []
        f_, l_ = re.escape(first), re.escape(last)
        # adjacent, either order, allowing a middle name or initial and a hyphenated last name ("Tayeb Jukaku", "Jukaku Tayeb")
        pats = [re.compile(rf"\b{f_}\W+(?:\w+\.?\W+)?{l_}\b|\b{l_},?\W+{f_}\b", re.I)]
    else:
        words = [w for w in re.findall(r"[A-Za-z&]+", row["contributor"]) if w.upper() not in ("INC", "LLC", "THE", "PAC")][:4]
        pats = [re.compile(r"\b" + r"\W+".join(map(re.escape, words)) + r"\b", re.I)] if words else []
    first_word = (norm_name(row["contributor"])[0] if row["entity_type"] == "IND" else "").lower()
    return sorted(h for h, t in texts.items()
                  if pats and (not first_word or first_word in lower[h]) and all(p.search(t) for p in pats))


receipts = []
for row in sorted(pac_all, key=lambda r: (r["committee"], -(r["amount"] or 0))):
    named = stories_naming(row)
    receipts.append({**row, "n_stories_naming_contributor": len(named), "story_ids": " ".join(named[:25])})
same = defaultdict(int)
for r in receipts:
    same[(r["committee"], r["contributor"].upper(), r["date"], r["amount"])] += 1
for r in receipts:
    r["duplicate_suspected"] = same[(r["committee"], r["contributor"].upper(), r["date"], r["amount"])] > 1

# ---- ties: one row per distinct (entity, link, counterparty or recipient) -------------------------
verdicts = {}
if VERDICTS.exists():
    for line in VERDICTS.open(encoding="utf-8"):
        if line.strip():
            v = json.loads(line)
            verdicts[v["tie_id"]] = v
ties = {}
for c, n in claim_entities:
    lt = c["link_type"]
    cp = c["recipient_norm"] if lt in DONATION else c["counterparty_norm"]
    tid = tie_id(n, lt, cp)
    t = ties.setdefault(tid, {"tie_id": tid, "entity": n, "kind": entities[n]["kind"], "link_type": lt, "counterparty": cp,
                              "claims": []})
    t["claims"].append(c)
tie_rows = []
for tid, t in ties.items():
    cs = sorted(t["claims"], key=lambda c: (c["published"] or "9999", c["claim_id"]))
    e = entities[t["entity"]]
    fec = {}
    if t["link_type"] == "donated_to_campaign" and e["kind"] == "person":
        fec = {"fec_amount": round(sum(d["net"] for d in e["campaign"]), 2) if e["campaign"] else 0.0,
               "fec_detail": f"{len(e['campaign'])} campaign donor record(s) under this name"}
    elif t["link_type"] == "donated_to_super_pac":
        rows = [p for p in e["pac"] if t["counterparty"] in (p["committee"], "unnamed super PAC supporting El-Sayed")]
        fec = {"fec_amount": round(sum(p["amount"] or 0 for p in rows), 2),
               "fec_detail": "; ".join(f"{p['committee']} {p['date']} ${p['amount']:,.0f} ({p['city']}, {p['state']})" for p in rows)}
    v = verdicts.get(tid, {})
    tie_rows.append({
        "tie_id": tid, "entity": t["entity"], "kind": t["kind"], "link_type": t["link_type"], "counterparty_or_recipient": t["counterparty"],
        "n_claims": len(cs), "n_stories": len({c["story_id"] for c in cs}), "n_outlets": len({c["outlet"] for c in cs}),
        "first_published": cs[0]["published"], "first_outlet": cs[0]["outlet"], "first_url": cs[0]["url"],
        "outlets": "; ".join(sorted({c["outlet"] or "" for c in cs})),
        "amounts_stated": "; ".join(sorted({f"${c['amount_usd']:,.0f}" for c in cs if isinstance(c["amount_usd"], (int, float))})),
        "characterizations": " | ".join(dict.fromkeys(c["counterparty_characterization"] for c in cs if c["counterparty_characterization"]))[:600],
        "first_quote": cs[0]["quote"], "evidence_urls_cited": " | ".join(sorted({u for c in cs for u in (c["evidence_urls"] or "").split(" | ") if u})),
        "fec_amount": fec.get("fec_amount"), "fec_detail": fec.get("fec_detail"),
        "verdict": v.get("verdict"), "verdict_status": v.get("status"), "confidence": v.get("confidence"),
        "verdict_reason": v.get("reason"), "identity_basis": v.get("identity_basis"),
        "characterization_check": v.get("characterization_check"),
        "content_verdict": v.get("content_verdict"), "content_ref": v.get("content_ref"),
        "primary_evidence": " | ".join(f"{e['kind']}: {e['url']} [{e.get('file')}]" for e in v.get("primary_evidence") or []),
        "review_issue": (v.get("review") or {}).get("issue") if not (v.get("review") or {}).get("agree", True) else None,
        "adjudication": (v.get("adjudication") or {}).get("note"), "verdict_round": v.get("round"), "claim_ids": " ".join(c["claim_id"] for c in cs),
    })
tie_rows.sort(key=lambda r: (-r["n_stories"], r["entity"]))


def dump(name: str, rows: list[dict]) -> None:
    with (OUT / f"{name}.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=list, ensure_ascii=False) + "\n")
    if rows:
        with (OUT / f"{name}.csv").open("w", encoding="utf-8", newline="") as f:
            fields = list(dict.fromkeys(k for r in rows for k in r))
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)


dump("stories", stories); dump("claims", claims); dump("links", links); dump("entities", ent_rows); dump("ties", tie_rows)
dump("fec_rows", fec_rows); dump("super_pac_receipts", receipts)
disp = defaultdict(int)
for s in stories:
    disp[s["disposition"]] += 1
unmapped = sorted({c["subject"] for c in claims if c["entity_kind"] == "unmapped"})
print(f"stories {len(stories)} {dict(sorted(disp.items()))}\nclaims {len(claims)} | links {len(links)} "
      f"(from in-scope stories {sum(1 for l in links if l['story_disposition'] == 'extracted_in_scope')}) | entities {len(ent_rows)} "
      f"(people with campaign FEC candidates {sum(1 for r in ent_rows if r['campaign_fec_candidates'])}, with super PAC rows "
      f"{sum(1 for r in ent_rows if r['super_pac_fec'])}) | ties {len(tie_rows)} (with verdicts {sum(1 for r in tie_rows if r['verdict'])})"
      f"\nunmapped subjects {len(unmapped)}: {unmapped[:20]}"
      f"\nverdicts whose tie no longer exists (subject remapped since judging): {len(set(verdicts) - set(ties))}")
