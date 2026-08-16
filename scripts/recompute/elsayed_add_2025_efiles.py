"""Add most-recent 2025 F3 e-files and rebuild the stored cycle roster + NPPES share."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
MOD = ROOT / "scripts" / "_oneoff" / "elsayed_nppes_and_q1.py"
spec = importlib.util.spec_from_file_location("elsayed_nppes_and_q1", MOD)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

DRAIN = m.DRAIN
OUT = m.OUT

FILES_2025 = [
    ("ye2025_2005717", "https://docquery.fec.gov/csv/717/2005717.csv",
     "https://docquery.fec.gov/dcdev/posted/2005717.fec"),
    ("q3_2025_2005716", "https://docquery.fec.gov/csv/716/2005716.csv",
     "https://docquery.fec.gov/dcdev/posted/2005716.fec"),
    ("h1_2025_2005714", "https://docquery.fec.gov/csv/714/2005714.csv",
     "https://docquery.fec.gov/dcdev/posted/2005714.fec"),
]


def main() -> int:
    extra = []
    meta = {}
    for label, csv_url, fec_url in FILES_2025:
        csv_p = m.download(csv_url, DRAIN / f"{label}.csv")
        fec_p = m.download(fec_url, DRAIN / f"{label}.fec")
        rows = m.parse_sa11ai(csv_p, label)
        extra.extend(rows)
        meta[label] = {
            "n": len(rows),
            "amt": round(sum(r["amt"] for r in rows), 2),
            "csv": str(csv_p),
            "fec": str(fec_p),
        }
    m.write_json("filings_2025_most_recent.json", meta)

    # prior 2026 e-file slices already parsed in previous run; re-parse from disk
    q1 = m.parse_sa11ai(DRAIN / "q1_2026_2005719.csv", "q1_amendment_2005719")
    q2 = m.parse_sa11ai(DRAIN / "q2_2026_2005720.csv", "q2_2005720")
    p12 = m.parse_sa11ai(DRAIN / "p12_2026_2005721.csv", "p12_2005721")
    roster = extra + q1 + q2 + p12
    m.write_jsonl(OUT / "roster_named_itemized.jsonl", roster)
    roster_sum = {
        "n": len(roster),
        "amt": round(sum(r["amt"] for r in roster), 2),
        "by_src": {},
        "form3_itemized": 10265431.61,
    }
    for src in sorted({r["src"] for r in roster}):
        sub = [r for r in roster if r["src"] == src]
        roster_sum["by_src"][src] = {"n": len(sub), "amt": round(sum(r["amt"] for r in sub), 2)}
    roster_sum["gap_vs_form3_itemized"] = round(10265431.61 - roster_sum["amt"], 2)
    m.write_json("roster_summary.json", roster_sum)

    keys = [(r["last_norm"], r["first_norm"], r["state"]) for r in roster
            if r["last_norm"] and r["first_norm"] and r["state"]]
    hits = m.nppes_match(keys)

    from collections import defaultdict
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
        if m.PHYS_OCC.search(r["occupation"] or ""):
            d["fec_physician_occ"] = True
        if m.CLIN_OCC.search(r["occupation"] or ""):
            d["fec_clinician_occ"] = True

    donor_rows = []
    buckets = defaultdict(lambda: {"n_donors": 0, "n_gifts": 0, "amt": 0.0})
    for k, d in donor.items():
        adj = m.adjudicate(hits.get(k, []))
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
    m.write_jsonl(OUT / "nppes_donor_matches.jsonl", donor_rows)
    m.write_jsonl(OUT / "nppes_donor_matches.ingest.jsonl", donor_rows)

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
    confirmed = (
        buckets["both_fec_and_nppes_physician"]["amt"]
        + buckets["nppes_physician_fec_silent"]["amt"]
    )
    sharpened = {
        "named_itemized_total": tot,
        "n_gifts": roster_sum["n"],
        "form3_itemized": 10265431.61,
        "gap_vs_form3_itemized": roster_sum["gap_vs_form3_itemized"],
        "form3_unitemized": 4142626.45,
        "nppes_confirmed_physician_dollars": round(confirmed, 2),
        "nppes_confirmed_physician_pct": round(100.0 * confirmed / tot, 2) if tot else 0,
        "fec_physician_unmatched_still_unconfirmed": round(buckets["fec_physician_unmatched"]["amt"], 2),
        "fec_physician_unique_nppes_nonphysician_dropped": round(
            buckets["fec_physician_nppes_unique_nonphysician"]["amt"], 2
        ),
        "fec_physician_ambiguous_nppes": round(
            buckets["fec_physician_nppes_ambiguous_or_mixed"]["amt"], 2
        ),
        "upper_bound_physician_if_unmatched_kept": round(
            confirmed
            + buckets["fec_physician_unmatched"]["amt"]
            + buckets["fec_physician_nppes_ambiguous_or_mixed"]["amt"],
            2,
        ),
        "buckets": bucket_out,
        "caught_consultants_n": sum(1 for r in donor_rows if r["label"] == "nppes_physician_fec_silent"),
        "caught_consultants_amt": round(buckets["nppes_physician_fec_silent"]["amt"], 2),
        "caught_consultants_sample": [
            r for r in donor_rows if r["label"] == "nppes_physician_fec_silent"
        ][:25],
        "dropped_false_physician_sample": [
            r for r in donor_rows if r["label"] == "fec_physician_unique_nppes_nonphysician"
        ][:25],
    }
    m.write_json("healthcare_share_nppes.json", sharpened)

    # queue again (date-stamped path to avoid QUEUE_NOOP)
    from src.ingest_queue import QueueRejected, queue_for_ingest_strict
    qpath = OUT / "nppes_donor_matches.ingest.cycle.jsonl"
    m.write_jsonl(qpath, donor_rows)
    try:
        entry = queue_for_ingest_strict(
            path=str(qpath),
            target_table="fec_c00902668_itemized_nppes_2026",
            source_url="https://docquery.fec.gov/cgi-bin/forms/C00902668/",
            vertical="political",
            sub_vertical="campaign_finance",
            description=(
                "C00902668 cycle named itemized donors from most-recent F3 e-files "
                "(2025 H1/Q3/YE + 2026 Q1/Q2/12P) joined to lake.nppes_full."
            ),
            aliases="El-Sayed, C00902668, NPPES, SA11AI",
            priority=70,
            queued_by="elsayed_add_2025_efiles.py",
        )
        qres = {"ok": True, "ledger_id": entry.get("ledger_id") if isinstance(entry, dict) else None}
    except QueueRejected as e:
        qres = {"ok": False, "error": str(e)}
    m.write_json("ingest_queue_receipt.json", qres)

    idx = json.loads((OUT / "analysis_index.json").read_text(encoding="utf-8"))
    idx["cycle_roster_rebuilt"] = True
    idx["headline"] = sharpened
    idx["artifacts"] = sorted({*idx.get("artifacts", []), "filings_2025_most_recent.json",
                               "roster_named_itemized.jsonl", "healthcare_share_nppes.json"})
    m.write_json("analysis_index.json", idx)

    (OUT / "healthcare_share_nppes.md").write_text(
        "\n".join([
            "# El-Sayed cycle named-itemized healthcare share (NPPES + most-recent F3 e-files)",
            "",
            f"Named itemized: ${tot:,.2f} / {roster_sum['n']} gifts",
            f"Gap vs Form 3 itemized $10,265,431.61: ${roster_sum['gap_vs_form3_itemized']:,.2f}",
            f"NPPES-confirmed physician: ${confirmed:,.2f} ({sharpened['nppes_confirmed_physician_pct']}%)",
            f"Caught FEC-silent NPPES physicians: ${sharpened['caught_consultants_amt']:,.2f} "
            f"({sharpened['caught_consultants_n']} name+state keys)",
            f"Dropped FEC-physician unique non-MD: ${sharpened['fec_physician_unique_nppes_nonphysician_dropped']:,.2f}",
            f"FEC-physician unmatched: ${sharpened['fec_physician_unmatched_still_unconfirmed']:,.2f}",
            f"FEC-physician ambiguous: ${sharpened['fec_physician_ambiguous_nppes']:,.2f}",
            f"Upper bound (confirmed + unmatched + ambiguous): "
            f"${sharpened['upper_bound_physician_if_unmatched_kept']:,.2f}",
            "",
            json.dumps(bucket_out, indent=2),
        ]),
        encoding="utf-8",
    )
    m.log(f"WROTE {OUT / 'healthcare_share_nppes.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
