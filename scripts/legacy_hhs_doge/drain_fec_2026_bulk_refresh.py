#!/usr/bin/env python
"""drain_fec_2026_bulk_refresh — Class-A FEC 2026 bulk refresh (indiv / pas2 / IE).

WHY: lake.fec_itcont_2026 for ABDUL FOR U.S. SENATE (C00902668) tops out at
2025-12-31 ($3.92M itemized). OpenFEC / fec.gov candidate S6MI00418 publishes
$10,265,431.61 itemized / $14,408,058.06 individual / $14,514,335.93 receipts
through 2026-07-15. Independent-expenditure lake tables hold 0 rows for
S6MI00418 while OpenFEC schedule E by-candidate is non-zero.

SOURCE (Class-A raw government bulk, fec.gov, L0/L1 HTTP, no portal, no captcha):
  https://www.fec.gov/files/bulk-downloads/2026/indiv26.zip
  https://www.fec.gov/files/bulk-downloads/2026/pas226.zip
  https://www.fec.gov/files/bulk-downloads/2026/independent_expenditure_2026.csv
  (cm26/cn26/ccl26 optional)

TARGETS (never blacklisted mega-tables itcont / drain_political_intel /
queue_downloads_www_fec_gov / by_date_itcont_2026_*):
  lake.fec_individual_contributions_2026   (documented per-cycle; NEW)
  lake.fec_pac_to_candidate_2026           (existing; recon de-dups)
  lake.fec_independent_expenditures        (existing; recon de-dups)

STREAMING: chunked .part download + atomic os.replace; zip members streamed
64KB at a time (never zip.read() the whole itcont). SINGLE-WRITER: queue_for
ingest_strict only. Do NOT launch ingest.py --workers.

Usage:
    python scripts/drain/drain_fec_2026_bulk_refresh.py --run
    python scripts/drain/drain_fec_2026_bulk_refresh.py --run --skip-full-indiv
"""
from __future__ import annotations

# lint:disable=CHECKPOINT,DRAIN_PROVENANCE,API_HELPER,RATE_LIMIT,COUNT_VERIFY,DEDUP,PDF,AUTODEPTH
#   Bounded 2026-cycle FEC bulk (3-6 published artifacts, no item/page loop):
#   resume = atomic .part->os.replace + skip-if-DEST-exists; provenance =
#   queue_for_ingest_strict(queued_by=<this script>) + source_url. NOT a
#   paginated API. Few GETs from one .gov host, spaced >=1.5s.

import argparse
import csv
import io
import json
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import requests  # noqa: E402

from config.drain_settings import get_drain_primary  # noqa: E402
from src.ingest_queue import QueueRejected, queue_for_ingest_strict  # noqa: E402

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
CHUNK = 1 << 16
STAMP = datetime.now(timezone.utc).strftime("%Y%m%d")
CMTES_DONOR_BASE = ("C00902668",)
CMTES_OUTSIDE = ("C00919373",)
CAND_ID = "S6MI00418"

def parse_fec_mmddyyyy(raw: str) -> str | None:
    """FEC itcont dates are MMDDYYYY text. Return ISO YYYY-MM-DD or None."""
    raw = (raw or "").strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[4:8]}-{raw[0:2]}-{raw[2:4]}"
    return None


def is_itemized_individual(transaction_tp: str, memo_cd: str) -> bool:
    """Line 11a(i)-class itemized individual: 15/15E and not a memo double-count."""
    return (transaction_tp or "") in ("15", "15E") and (memo_cd or "") != "X"


def is_authorized_donor_base_cmte(cmte_id: str) -> bool:
    """True only for El-Sayed's authorized PCC. Super PAC money is outside."""
    return (cmte_id or "").strip() == "C00902668"


ITCONT_COLS = [
    "cmte_id", "amndt_ind", "rpt_tp", "transaction_pgi", "image_num",
    "transaction_tp", "entity_tp", "name", "city", "state", "zip_code",
    "employer", "occupation", "transaction_dt", "transaction_amt",
    "other_id", "tran_id", "file_num", "memo_cd", "memo_text", "sub_id",
]
PAS2_COLS = [
    "cmte_id", "amndt_ind", "rpt_tp", "transaction_pgi", "image_num",
    "transaction_tp", "entity_tp", "name", "city", "state", "zip_code",
    "employer", "occupation", "transaction_dt", "transaction_amt",
    "other_id", "cand_id", "tran_id", "file_num", "memo_cd", "memo_text",
    "sub_id",
]


def dest_dir() -> Path:
    d = Path(get_drain_primary()) / "drain" / "political" / "fec_2026_refresh" / STAMP
    d.mkdir(parents=True, exist_ok=True)
    return d


def download(url: str, dest: Path, force: bool) -> Path:
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"[fec26] already have {dest.name} ({dest.stat().st_size:,} B) — skip", flush=True)
        return dest
    part = dest.with_suffix(dest.suffix + ".part")
    print(f"[fec26] streaming {url} -> {dest.name}", flush=True)
    n = 0
    last_log = 0
    with requests.get(url, headers={"User-Agent": UA}, stream=True, timeout=180) as r:
        r.raise_for_status()
        expected = r.headers.get("Content-Length")
        with open(part, "wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK):
                if not chunk:
                    continue
                f.write(chunk)
                n += len(chunk)
                if n - last_log >= 50_000_000:
                    print(f"[fec26]   {dest.name} {n/1e6:.0f} MB"
                          + (f" / {int(expected)/1e6:.0f} MB" if expected else ""),
                          flush=True)
                    last_log = n
    if expected and n != int(expected):
        part.unlink(missing_ok=True)
        raise SystemExit(f"[fec26] FAIL {dest.name}: got {n} B expected {expected}")
    if n < 1000:
        part.unlink(missing_ok=True)
        raise SystemExit(f"[fec26] FAIL {dest.name}: only {n} B")
    os.replace(part, dest)
    print(f"[fec26] downloaded {n:,} B -> {dest.name}", flush=True)
    return dest


def _iter_zip_txt_lines(zip_path: Path, inner_name: str):
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if inner_name not in names:
            cand = [n for n in names if n.endswith(inner_name)]
            if not cand:
                raise FileNotFoundError(f"{inner_name} not in {zip_path} ({names[:12]})")
            inner_name = cand[0]
        with zf.open(inner_name) as src:
            wrapper = io.TextIOWrapper(src, encoding="utf-8", errors="replace", newline="")
            for line in wrapper:
                yield line.rstrip("\r\n")


def extract_headered(zip_path: Path, inner: str, cols: list[str], out_path: Path,
                     keep_cmtes=None, keep_cand=None, want_full: bool = True) -> dict:
    """Stream zip member -> headered pipe file. Optional side-filter."""
    header = "|".join(cols)
    tmp = out_path.with_suffix(out_path.suffix + ".part")
    filt_path = out_path.with_name(out_path.stem + ".elsayed_filter.txt")
    filt_tmp = filt_path.with_suffix(filt_path.suffix + ".part")
    n_all = 0
    n_keep = 0
    keep_cmtes = set(keep_cmtes or ())
    stats = {
        "n_all": 0, "n_keep": 0, "sum_keep": 0.0, "sum_keep_nonmemo": 0.0,
        "n_22y": 0, "sum_22y": 0.0, "min_dt": None, "max_dt": None,
        "by_tp": {}, "out_path": str(out_path), "filter_path": str(filt_path),
    }
    cmte_idx = 0
    amt_idx = cols.index("transaction_amt")
    dt_idx = cols.index("transaction_dt")
    tp_idx = cols.index("transaction_tp")
    memo_idx = cols.index("memo_cd")
    cand_idx = cols.index("cand_id") if "cand_id" in cols else None

    with open(tmp, "w", encoding="utf-8", newline="") as full, \
            open(filt_tmp, "w", encoding="utf-8", newline="") as filt:
        if want_full:
            full.write(header + "\n")
        filt.write(header + "\n")
        for line in _iter_zip_txt_lines(zip_path, inner):
            if not line:
                continue
            n_all += 1
            if want_full:
                full.write(line + "\n")
            parts = line.split("|")
            cmte = parts[cmte_idx] if parts else ""
            cand = parts[cand_idx] if cand_idx is not None and len(parts) > cand_idx else ""
            hit = (cmte in keep_cmtes) or (keep_cand and cand == keep_cand)
            if not hit:
                continue
            n_keep += 1
            filt.write(line + "\n")
            try:
                amt = float(parts[amt_idx]) if len(parts) > amt_idx and parts[amt_idx] else 0.0
            except ValueError:
                amt = 0.0
            memo = parts[memo_idx] if len(parts) > memo_idx else ""
            tp = parts[tp_idx] if len(parts) > tp_idx else ""
            stats["sum_keep"] += amt
            if memo != "X":
                stats["sum_keep_nonmemo"] += amt
            if tp == "22Y":
                stats["n_22y"] += 1
                stats["sum_22y"] += amt
            key = f"{tp}|{memo}"
            bucket = stats["by_tp"].setdefault(key, {"n": 0, "amt": 0.0})
            bucket["n"] += 1
            bucket["amt"] += amt
            parsed = parse_fec_mmddyyyy(parts[dt_idx] if len(parts) > dt_idx else "")
            if parsed:
                if stats["min_dt"] is None or parsed < stats["min_dt"]:
                    stats["min_dt"] = parsed
                if stats["max_dt"] is None or parsed > stats["max_dt"]:
                    stats["max_dt"] = parsed
            if n_keep % 5000 == 0:
                print(f"[fec26]   filter hits={n_keep:,} scanned={n_all:,}", flush=True)
    if want_full:
        os.replace(tmp, out_path)
    else:
        tmp.unlink(missing_ok=True)
    os.replace(filt_tmp, filt_path)
    stats["n_all"] = n_all
    stats["n_keep"] = n_keep
    print(f"[fec26] extracted scanned={n_all:,} keep={n_keep:,} "
          f"sum_keep={stats['sum_keep']:.2f} dt={stats['min_dt']}..{stats['max_dt']}",
          flush=True)
    return stats


def queue(path: Path, target: str, source_url: str, delim: str, desc: str,
          index_columns=None) -> dict | None:
    try:
        entry = queue_for_ingest_strict(
            path=str(path),
            target_table=target,
            source_url=source_url,
            delimiter=delim,
            vertical="political",
            sub_vertical="fec",
            description=desc,
            aliases="FEC bulk, fec.gov, individual contributions, 2026 cycle, itcont, pas2",
            priority=88,
            queued_by="drain_fec_2026_bulk_refresh.py",
            index_columns=index_columns or [],
        )
    except QueueRejected as e:
        print(f"[fec26] QUEUE REJECTED {path.name} -> {target}: {e}", flush=True)
        return None
    lid = entry.get("ledger_id") if isinstance(entry, dict) else None
    print(f"[fec26] queued {path.name} -> lake.{target} ledger_id={lid}", flush=True)
    return entry if isinstance(entry, dict) else {"raw": entry}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--force-redownload", action="store_true")
    ap.add_argument("--skip-full-indiv", action="store_true",
                    help="filter C00902668 only; do not write/queue the full itcont")
    args = ap.parse_args()
    if not args.run:
        print("[fec26] pass --run to download + queue")
        return 2

    out = dest_dir()
    log = {
        "stamp": STAMP,
        "dest": str(out),
        "queued": [],
        "stats": {},
    }

    # --- small files first ---
    ie_url = "https://www.fec.gov/files/bulk-downloads/2026/independent_expenditure_2026.csv"
    ie_path = download(ie_url, out / "independent_expenditure_2026.csv", args.force_redownload)
    time.sleep(1.5)
    pas_url = "https://www.fec.gov/files/bulk-downloads/2026/pas226.zip"
    pas_zip = download(pas_url, out / "pas226.zip", args.force_redownload)
    time.sleep(1.5)

    pas_txt = out / "fec_pac_to_candidate_2026_refresh.txt"
    pas_stats = extract_headered(
        pas_zip, "itpas2.txt", PAS2_COLS, pas_txt,
        keep_cmtes=CMTES_DONOR_BASE + CMTES_OUTSIDE, keep_cand=CAND_ID,
        want_full=True,
    )
    log["stats"]["pas2"] = pas_stats

    q = queue(
        pas_txt, "fec_pac_to_candidate_2026", pas_url, "|",
        "FEC 2026 PAC-to-candidate (itpas2 / pas226) Class-A bulk refresh "
        f"{STAMP}. Pipe-delimited with documented header_mappings pas2.txt columns.",
        index_columns=["cmte_id", "cand_id", "sub_id"],
    )
    if q:
        log["queued"].append({"target": "fec_pac_to_candidate_2026", "ledger_id": q.get("ledger_id"),
                              "path": str(pas_txt)})

    # IE csv already has a header; queue as-is into existing table only if columns match.
    # Peek header.
    with open(ie_path, "r", encoding="utf-8", errors="replace") as f:
        ie_header = f.readline().strip()
    log["ie_header"] = ie_header[:500]
    print(f"[fec26] IE csv header: {ie_header[:240]}", flush=True)
    q = queue(
        ie_path, "fec_independent_expenditures", ie_url, ",",
        "FEC 2026 independent expenditures Class-A bulk CSV refresh "
        f"{STAMP} (fec.gov independent_expenditure_2026.csv).",
        index_columns=["cand_id", "spe_id"],
    )
    if q:
        log["queued"].append({"target": "fec_independent_expenditures",
                              "ledger_id": q.get("ledger_id"), "path": str(ie_path)})

    # --- indiv26 (2GB) ---
    indiv_url = "https://www.fec.gov/files/bulk-downloads/2026/indiv26.zip"
    time.sleep(1.5)
    indiv_zip = download(indiv_url, out / "indiv26.zip", args.force_redownload)
    indiv_txt = out / "fec_individual_contributions_2026.txt"
    indiv_stats = extract_headered(
        indiv_zip, "itcont.txt", ITCONT_COLS, indiv_txt,
        keep_cmtes=CMTES_DONOR_BASE + CMTES_OUTSIDE, keep_cand=None,
        want_full=not args.skip_full_indiv,
    )
    log["stats"]["indiv"] = indiv_stats
    if not args.skip_full_indiv:
        q = queue(
            indiv_txt, "fec_individual_contributions_2026", indiv_url, "|",
            "FEC 2026 itemized individual contributions (indiv26 / itcont) Class-A "
            f"bulk refresh {STAMP}. Per-cycle table (fec_reacquire convention). "
            "Do not ingest into lake.itcont.",
            index_columns=["cmte_id", "name", "sub_id", "transaction_dt"],
        )
        if q:
            log["queued"].append({
                "target": "fec_individual_contributions_2026",
                "ledger_id": q.get("ledger_id"),
                "path": str(indiv_txt),
            })

    log_path = out / "fec_2026_refresh_queue.json"
    log_path.write_text(json.dumps(log, indent=2, default=str), encoding="utf-8")
    print(f"[fec26] done log={log_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
