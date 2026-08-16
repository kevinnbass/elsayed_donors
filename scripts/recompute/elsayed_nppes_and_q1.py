"""El-Sayed donor-base sharpen: Q1 amendment delta + NPPES MD match + persist.

Writes under outputs/el_sayed_donor_base/ as it goes. Queues a compact
donor-level JSONL for lake ingest. Does not launch ingest workers.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.db import get_connection  # noqa: E402
from src.ingest_queue import QueueRejected, queue_for_ingest_strict  # noqa: E402

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
OUT = ROOT / "outputs" / "el_sayed_donor_base"
DRAIN = Path(r"K:/drain/political/fec_2026_refresh/20260816/filings")
FILT = Path(r"K:/drain/political/fec_2026_refresh/20260816/fec_individual_contributions_2026.elsayed_filter.txt")
OUT.mkdir(parents=True, exist_ok=True)

I_ENTITY, I_LAST, I_FIRST = 5, 7, 8
I_CITY, I_ST, I_ZIP = 14, 15, 16
I_DATE, I_AMT, I_EMP, I_OCC = 19, 20, 23, 24

PHYS_OCC = re.compile(
    r"PHYSICIAN|DOCTOR|SURGEON|MD\b|CARDIOLOG|ONCOLOG|PEDIATRICIAN|"
    r"PSYCHIATRIST|ANESTHESI|RADIOLOGIST|NEUROLOGIST|DERMATOLOG|"
    r"HOSPITALIST|INTENSIVIST|PATHOLOGIST|OB.?GYN|ORTHOPED",
    re.I,
)
CLIN_OCC = re.compile(
    r"\b(PHYSICIAN|DOCTOR|SURGEON|MD\b|DENTIST|PHARMACIST|NURSE|RN\b|"
    r"NURSE PRACTITIONER|PHYSICIAN ASSISTANT|PSYCHOLOGIST|THERAPIST|"
    r"CHIROPRACT|OPTOMETR|SOCIAL WORKER|CARDIOLOG|ONCOLOG|RADIOLOG|"
    r"DERMATOLOG|HOSPITALIST|NEPHROLOG|OPHTHALM)",
    re.I,
)

# CMS NUCC: 207/208 = allopathic & osteopathic physicians
PHYS_TAX = re.compile(r"^(207|208)")
DENT_TAX = re.compile(r"^122")
PHARM_TAX = re.compile(r"^1835")
RN_TAX = re.compile(r"^163W")
NP_TAX = re.compile(r"^363L")
PA_TAX = re.compile(r"^363A")


def log(msg: str) -> None:
    print(msg, flush=True)


def write_json(name: str, obj) -> Path:
    p = OUT / name
    p.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
    log(f"WROTE {p} ({p.stat().st_size:,} B)")
    return p


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        log(f"have {dest.name} {dest.stat().st_size:,}")
        return dest
    log(f"GET {url}")
    r = requests.get(url, headers={"User-Agent": UA}, timeout=180)
    log(f"  {r.status_code} {len(r.content):,} {r.headers.get('Content-Type')}")
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def norm_token(s: str) -> str:
    s = (s or "").upper()
    s = s.replace("'", "").replace(".", "")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def split_fec_name(name: str) -> tuple[str, str]:
    name = (name or "").strip()
    if "," in name:
        last, rest = name.split(",", 1)
    else:
        parts = name.split()
        last, rest = (parts[0] if parts else ""), " ".join(parts[1:])
    first = rest.strip().split()[0] if rest.strip() else ""
    return norm_token(last), norm_token(first)


def parse_sa11ai(path: Path, src: str) -> list[dict]:
    text = path.read_bytes().decode("latin-1", errors="replace")
    out = []
    n_sa = n_x = 0
    amt_all = amt_keep = 0.0
    for row in csv.reader(io.StringIO(text)):
        if not row or row[0] != "SA11AI":
            continue
        n_sa += 1
        if len(row) < 25:
            continue
        memo_cd = ((row[42] if len(row) > 42 else "") or (row[41] if len(row) > 41 else "")).strip()
        memo_text = (row[43] if len(row) > 43 else "") or ""
        try:
            amt = float(row[I_AMT] or 0)
        except ValueError:
            amt = 0.0
        amt_all += amt
        if memo_cd.upper() == "X":
            n_x += 1
            continue
        amt_keep += amt
        last = (row[I_LAST] or "").strip()
        first = (row[I_FIRST] or "").strip()
        name = f"{last}, {first}".strip(", ")
        last_n, first_n = split_fec_name(name)
        rec = {
            "src": src,
            "tran_id": row[2] if len(row) > 2 else "",
            "name": name,
            "last_norm": last_n,
            "first_norm": first_n,
            "city": (row[I_CITY] or "").strip(),
            "state": (row[I_ST] or "").strip().upper(),
            "zip": (row[I_ZIP] or "").strip(),
            "date": (row[I_DATE] or "").strip(),
            "amt": amt,
            "employer": (row[I_EMP] or "").strip(),
            "occupation": (row[I_OCC] or "").strip(),
            "entity": (row[I_ENTITY] or "").strip(),
            "memo_cd": memo_cd,
            "memo_text": memo_text[:160],
        }
        out.append(rec)
    log(f"parse {src}: SA11AI={n_sa} memoX={n_x} kept={len(out)} "
        f"amt_all={amt_all:.2f} amt_keep={amt_keep:.2f}")
    return out


def parse_indiv26_q1() -> list[dict]:
    out = []
    with open(FILT, encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f, delimiter="|"):
            if (row.get("cmte_id") or "").strip() != "C00902668":
                continue
            if (row.get("file_num") or "").strip() != "1996846":
                continue
            tp = row.get("transaction_tp") or ""
            memo = row.get("memo_cd") or ""
            if tp not in ("15", "15E") or memo == "X":
                continue
            try:
                amt = float(row.get("transaction_amt") or 0)
            except ValueError:
                amt = 0.0
            name = (row.get("name") or "").strip()
            last_n, first_n = split_fec_name(name)
            out.append({
                "src": "indiv26_file_1996846",
                "tran_id": row.get("tran_id") or "",
                "name": name,
                "last_norm": last_n,
                "first_norm": first_n,
                "city": (row.get("city") or "").strip(),
                "state": (row.get("state") or "").strip().upper(),
                "zip": (row.get("zip_code") or "").strip(),
                "date": row.get("transaction_dt") or "",
                "amt": amt,
                "employer": (row.get("employer") or "").strip(),
                "occupation": (row.get("occupation") or "").strip(),
                "entity": (row.get("entity_tp") or "").strip(),
                "memo_cd": memo,
                "memo_text": (row.get("memo_text") or "")[:160],
            })
    log(f"parse indiv26 Q1 file_num=1996846 kept={len(out)} amt={sum(r['amt'] for r in out):.2f}")
    return out


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"WROTE {path} rows={len(rows)} ({path.stat().st_size:,} B)")


def tax_class(code: str) -> str:
    c = (code or "").strip()
    if PHYS_TAX.match(c):
        return "physician"
    if DENT_TAX.match(c):
        return "dentist"
    if PHARM_TAX.match(c):
        return "pharmacist"
    if NP_TAX.match(c):
        return "np"
    if PA_TAX.match(c):
        return "pa"
    if RN_TAX.match(c):
        return "rn"
    if c:
        return "other_nppes"
    return "none"


def nppes_match(keys: list[tuple[str, str, str]]) -> dict[tuple[str, str, str], list[dict]]:
    """keys = (last_norm, first_norm, state). Returns hits from lake.nppes_full."""
    con = get_connection()
    con.execute("SET statement_timeout = '300s'")
    con.execute("SET lock_timeout = '20s'")
    con.execute("DROP TABLE IF EXISTS tmp_elsayed_nppes_keys")
    con.execute(
        """
        CREATE TEMP TABLE tmp_elsayed_nppes_keys (
            last_norm text, first_norm text, state text
        )
        """
    )
    uniq = sorted(set(keys))
    con.executemany(
        "INSERT INTO tmp_elsayed_nppes_keys VALUES (%s,%s,%s)",
        uniq,
    )
    log(f"NPPES keys loaded {len(uniq)}")
    rows = con.execute(
        """
        SELECT k.last_norm, k.first_norm, k.state,
               n.npi, n.provider_last_name, n.provider_first_name,
               n.provider_credential, n.provider_practice_state,
               n.provider_mailing_state, n.taxonomy_code_1,
               n.npi_deactivation_date, n.entity_type
        FROM tmp_elsayed_nppes_keys k
        JOIN lake.nppes_full n
          ON n.entity_type = 1
         AND upper(regexp_replace(n.provider_last_name, '[^A-Za-z0-9]+', ' ', 'g'))
             = k.last_norm
         AND split_part(
               upper(regexp_replace(n.provider_first_name, '[^A-Za-z0-9]+', ' ', 'g')),
               ' ', 1
             ) = k.first_norm
         AND (
               n.provider_practice_state = k.state
            OR n.provider_mailing_state = k.state
         )
        """
    ).fetchall()
    log(f"NPPES join hits {len(rows)}")
    by: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in rows:
        key = (r[0], r[1], r[2])
        by[key].append({
            "npi": r[3],
            "nppes_last": r[4],
            "nppes_first": r[5],
            "credential": r[6],
            "practice_state": r[7],
            "mailing_state": r[8],
            "taxonomy": r[9],
            "deactivated": r[10],
            "entity_type": r[11],
            "tax_class": tax_class(r[9] or ""),
        })
    con.close()
    return by


def adjudicate(hits: list[dict]) -> dict:
    if not hits:
        return {"verdict": "unmatched", "n_npi": 0, "n_physician_npi": 0,
                "unique": False, "taxonomies": []}
    phys = [h for h in hits if h["tax_class"] == "physician"]
    taxes = sorted({h["taxonomy"] for h in hits if h["taxonomy"]})
    unique = len(hits) == 1
    if unique and phys:
        v = "confirmed_physician"
    elif unique and not phys:
        v = "confirmed_nonphysician"
    elif phys and len(phys) == len(hits):
        v = "all_hits_physician_ambiguous"
    elif phys:
        v = "mixed_hits_some_physician"
    else:
        v = "matched_nonphysician_ambiguous"
    return {
        "verdict": v,
        "n_npi": len(hits),
        "n_physician_npi": len(phys),
        "unique": unique,
        "taxonomies": taxes[:8],
        "npis": [h["npi"] for h in hits[:8]],
        "credentials": sorted({(h["credential"] or "") for h in hits})[:6],
    }


def head_indiv26() -> dict:
    url = "https://www.fec.gov/files/bulk-downloads/2026/indiv26.zip"
    r = requests.head(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
    return {
        "url": url,
        "status": r.status_code,
        "content_length": r.headers.get("Content-Length"),
        "last_modified": r.headers.get("Last-Modified"),
        "prior_download_last_modified": "Sun, 16 Aug 2026 15:50:15 GMT",
        "prior_download_bytes": 2098465857,
        "newer_than_prior": (r.headers.get("Last-Modified") or "")
        != "Sun, 16 Aug 2026 15:50:15 GMT",
    }


def main() -> int:
    index = {"started_at": datetime.now(timezone.utc).isoformat(), "artifacts": []}

    # --- 1. Q1 most-recent amendment ---
    q1_csv = download(
        "https://docquery.fec.gov/csv/719/2005719.csv",
        DRAIN / "q1_2026_2005719.csv",
    )
    q1_fec = download(
        "https://docquery.fec.gov/dcdev/posted/2005719.fec",
        DRAIN / "q1_2026_2005719.fec",
    )
    q1_new = parse_sa11ai(q1_csv, "q1_amendment_2005719")
    q1_old = parse_indiv26_q1()
    old_amt = sum(r["amt"] for r in q1_old)
    new_amt = sum(r["amt"] for r in q1_new)
    old_ids = {r["tran_id"] for r in q1_old if r["tran_id"]}
    new_ids = {r["tran_id"] for r in q1_new if r["tran_id"]}
    delta = {
        "indiv26_file_1996846": {"n": len(q1_old), "amt": round(old_amt, 2)},
        "e_file_2005719_most_recent": {"n": len(q1_new), "amt": round(new_amt, 2)},
        "amt_delta_new_minus_old": round(new_amt - old_amt, 2),
        "n_delta": len(q1_new) - len(q1_old),
        "tran_ids_only_in_amendment": len(new_ids - old_ids),
        "tran_ids_only_in_indiv26": len(old_ids - new_ids),
        "q1_csv": str(q1_csv),
        "q1_fec": str(q1_fec),
        "note": "Most-recent Q1 e-file replaces indiv26 file_num 1996846 as the Q1 slice.",
    }
    write_json("q1_amendment_delta.json", delta)
    index["artifacts"].append("q1_amendment_delta.json")

    # --- 2. Canonical named roster: most-recent Q1 + Q2 + 12P e-files ---
    q2 = parse_sa11ai(DRAIN / "q2_2026_2005720.csv", "q2_2005720")
    p12 = parse_sa11ai(DRAIN / "p12_2026_2005721.csv", "p12_2005721")
    roster = q1_new + q2 + p12
    roster_path = OUT / "roster_named_itemized.jsonl"
    write_jsonl(roster_path, roster)
    index["artifacts"].append("roster_named_itemized.jsonl")
    roster_sum = {
        "n": len(roster),
        "amt": round(sum(r["amt"] for r in roster), 2),
        "by_src": {},
        "form3_itemized": 10265431.61,
    }
    for src in ("q1_amendment_2005719", "q2_2005720", "p12_2005721"):
        sub = [r for r in roster if r["src"] == src]
        roster_sum["by_src"][src] = {"n": len(sub), "amt": round(sum(r["amt"] for r in sub), 2)}
    roster_sum["gap_vs_form3_itemized"] = round(10265431.61 - roster_sum["amt"], 2)
    write_json("roster_summary.json", roster_sum)
    index["artifacts"].append("roster_summary.json")

    # --- 3. NPPES match ---
    keys = [(r["last_norm"], r["first_norm"], r["state"]) for r in roster
            if r["last_norm"] and r["first_norm"] and r["state"]]
    hits = nppes_match(keys)
    # donor-level (name+state) dollars
    donor = defaultdict(lambda: {
        "amt": 0.0, "n": 0, "name": "", "state": "",
        "last_norm": "", "first_norm": "",
        "occs": set(), "emps": set(),
        "fec_physician_occ": False, "fec_clinician_occ": False,
    })
    for r in roster:
        k = (r["last_norm"], r["first_norm"], r["state"])
        d = donor[k]
        d["amt"] += r["amt"]
        d["n"] += 1
        d["name"] = r["name"]
        d["state"] = r["state"]
        d["last_norm"] = r["last_norm"]
        d["first_norm"] = r["first_norm"]
        d["occs"].add(r["occupation"])
        d["emps"].add(r["employer"])
        if PHYS_OCC.search(r["occupation"] or ""):
            d["fec_physician_occ"] = True
        if CLIN_OCC.search(r["occupation"] or ""):
            d["fec_clinician_occ"] = True

    donor_rows = []
    buckets = defaultdict(lambda: {"n_donors": 0, "n_gifts": 0, "amt": 0.0})
    for k, d in donor.items():
        adj = adjudicate(hits.get(k, []))
        fec_phys = d["fec_physician_occ"]
        nppes_phys = adj["n_physician_npi"] > 0
        if nppes_phys and fec_phys:
            label = "both_fec_and_nppes_physician"
        elif nppes_phys and not fec_phys:
            label = "nppes_physician_fec_silent"
        elif fec_phys and adj["verdict"] == "confirmed_nonphysician":
            label = "fec_physician_nppes_unique_nonphysician"
        elif fec_phys and adj["verdict"] == "unmatched":
            label = "fec_physician_unmatched"
        elif fec_phys:
            label = "fec_physician_nppes_ambiguous_or_mixed"
        else:
            label = "not_fec_physician"
        rec = {
            "name": d["name"],
            "state": d["state"],
            "last_norm": d["last_norm"],
            "first_norm": d["first_norm"],
            "n_gifts": d["n"],
            "amt": round(d["amt"], 2),
            "fec_physician_occ": fec_phys,
            "fec_clinician_occ": d["fec_clinician_occ"],
            "occupations": sorted(d["occs"])[:8],
            "employers": sorted(d["emps"])[:8],
            "nppes_verdict": adj["verdict"],
            "n_npi": adj["n_npi"],
            "n_physician_npi": adj["n_physician_npi"],
            "taxonomies": adj.get("taxonomies", []),
            "npis": adj.get("npis", []),
            "label": label,
        }
        donor_rows.append(rec)
        buckets[label]["n_donors"] += 1
        buckets[label]["n_gifts"] += d["n"]
        buckets[label]["amt"] += d["amt"]

    donor_rows.sort(key=lambda r: -r["amt"])
    write_jsonl(OUT / "nppes_donor_matches.jsonl", donor_rows)
    index["artifacts"].append("nppes_donor_matches.jsonl")

    tot = roster_sum["amt"]
    bucket_out = {
        lab: {
            "n_donors": b["n_donors"],
            "n_gifts": b["n_gifts"],
            "amt": round(b["amt"], 2),
            "pct_of_named_itemized": round(100.0 * b["amt"] / tot, 2) if tot else 0,
        }
        for lab, b in sorted(buckets.items(), key=lambda kv: -kv[1]["amt"])
    }
    # sharpened physician $
    confirmed = (
        buckets["both_fec_and_nppes_physician"]["amt"]
        + buckets["nppes_physician_fec_silent"]["amt"]
    )
    fec_only_unmatched = buckets["fec_physician_unmatched"]["amt"]
    fec_false = buckets["fec_physician_nppes_unique_nonphysician"]["amt"]
    fec_ambig = buckets["fec_physician_nppes_ambiguous_or_mixed"]["amt"]
    sharpened = {
        "named_itemized_total": tot,
        "form3_itemized": 10265431.61,
        "form3_unitemized": 4142626.45,
        "nppes_confirmed_physician_dollars": round(confirmed, 2),
        "nppes_confirmed_physician_pct": round(100.0 * confirmed / tot, 2) if tot else 0,
        "fec_physician_unmatched_still_unconfirmed": round(fec_only_unmatched, 2),
        "fec_physician_unique_nppes_nonphysician_dropped": round(fec_false, 2),
        "fec_physician_ambiguous_nppes": round(fec_ambig, 2),
        "upper_bound_physician_if_unmatched_kept": round(
            confirmed + fec_only_unmatched + fec_ambig, 2
        ),
        "buckets": bucket_out,
        "caught_consultants_sample": [
            r for r in donor_rows
            if r["label"] == "nppes_physician_fec_silent"
        ][:20],
        "dropped_false_physician_sample": [
            r for r in donor_rows
            if r["label"] == "fec_physician_unique_nppes_nonphysician"
        ][:20],
    }
    write_json("healthcare_share_nppes.json", sharpened)
    index["artifacts"].append("healthcare_share_nppes.json")

    # --- 4. indiv26 vintage ---
    vintage = head_indiv26()
    con = get_connection()
    led = con.execute(
        """
        SELECT ledger_id, target_table, status, rows_inserted, error,
               queued_at, completed_at, LEFT(file_path,160)
        FROM infra.ingest_ledger
        WHERE ledger_id IN (2314347,2314348,2314349)
        ORDER BY ledger_id
        """
    ).fetchall()
    con.close()
    vintage["ingest_ledger"] = [
        {
            "ledger_id": r[0], "target": r[1], "status": r[2],
            "rows_inserted": r[3], "error": r[4],
            "queued_at": str(r[5]), "completed_at": str(r[6]), "path": r[7],
        }
        for r in led
    ]
    vintage["decision"] = (
        "Do not re-download indiv26 unless Last-Modified advances. "
        "Q2/12P itemizations are in the e-files, not in the 2026-08-16 bulk. "
        "Canonical named roster is the three most-recent F3 e-files, persisted here. "
        "Queued 30M-row fec_individual_contributions_2026 remains pending; "
        "no second ingest worker started."
    )
    write_json("indiv26_vintage.json", vintage)
    index["artifacts"].append("indiv26_vintage.json")

    # --- 5. queue compact donor-level JSONL ---
    qpath = OUT / "nppes_donor_matches.ingest.jsonl"
    write_jsonl(qpath, donor_rows)
    try:
        entry = queue_for_ingest_strict(
            path=str(qpath),
            target_table="fec_c00902668_itemized_nppes_2026",
            source_url="https://docquery.fec.gov/cgi-bin/forms/C00902668/",
            delimiter="",
            vertical="political",
            sub_vertical="campaign_finance",
            description=(
                "Abdul El-Sayed C00902668 named itemized donors (most-recent Q1+Q2+12P "
                "F3 SA11AI) joined to lake.nppes_full on last+first+state. Analysis "
                "table, not a FEC bulk replacement."
            ),
            aliases="El-Sayed, C00902668, NPPES physician match, SA11AI",
            priority=70,
            queued_by="elsayed_nppes_and_q1.py",
        )
        qres = {"ok": True, "ledger_id": (entry or {}).get("ledger_id") if isinstance(entry, dict) else None}
    except QueueRejected as e:
        qres = {"ok": False, "error": str(e)}
    write_json("ingest_queue_receipt.json", qres)
    index["artifacts"].append("ingest_queue_receipt.json")

    index["finished_at"] = datetime.now(timezone.utc).isoformat()
    index["headline"] = sharpened
    write_json("analysis_index.json", index)

    md = OUT / "healthcare_share_nppes.md"
    md.write_text(
        "\n".join([
            "# El-Sayed named-itemized healthcare share after NPPES + Q1 amendment",
            "",
            f"Named itemized total: ${tot:,.2f} (n={roster_sum['n']})",
            f"Q1 amendment delta vs indiv26: ${delta['amt_delta_new_minus_old']:,.2f}",
            f"Gap vs Form 3 itemized $10,265,431.61: ${roster_sum['gap_vs_form3_itemized']:,.2f}",
            "",
            f"NPPES-confirmed physician $: ${confirmed:,.2f} ({sharpened['nppes_confirmed_physician_pct']}% of named itemized)",
            f"FEC-physician unmatched (no NPPES): ${fec_only_unmatched:,.2f}",
            f"FEC-physician unique NPPES non-physician (dropped): ${fec_false:,.2f}",
            f"FEC-physician ambiguous NPPES: ${fec_ambig:,.2f}",
            f"Upper bound if unmatched+ambiguous kept: ${sharpened['upper_bound_physician_if_unmatched_kept']:,.2f}",
            "",
            "Buckets:",
            json.dumps(bucket_out, indent=2),
        ]),
        encoding="utf-8",
    )
    log(f"WROTE {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
