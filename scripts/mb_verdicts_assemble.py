"""Assemble tie verdicts from the research lanes, their rechecks and their adversarial reviews.

Usage: python scripts/mb_verdicts_assemble.py <lanes_dir> <evidence_store>
  <lanes_dir>/L*/        research lanes: packet.jsonl, verdicts.jsonl, sources.jsonl, evidence/<sha256>.<ext>
  <lanes_dir>/R_L*/      adversarial reviews: review.jsonl (+ evidence/ for new records)
  <evidence_store>       durable copy of every cited record, named <sha256>.<ext> (outside the repo)
Curated input: analysis/private/mb_adjudications.jsonl  one decision per disputed tie
  {"tie_id", "final_verdict", "decision": "lane"|"review"|"own", "note"}
Writes analysis/private/mb_verdicts.jsonl (one row per tie), mb_adjudication_todo.jsonl (disputes not yet decided)
and mb_sources.jsonl (every record a lane or reviewer saved, all kept in the store, cited or not).

A round-two lane line supersedes the round-one line for the same tie (it re-judged the tie against all its claims).
A review that agrees leaves the verdict as is; a disagreement stands as `disputed` until adjudicated. A written\nadjudication overrides any verdict (the final pass may also correct a verdict both engines agreed on).
"""
from __future__ import annotations

import glob
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANES, STORE = Path(sys.argv[1]), Path(sys.argv[2])
PRIVATE = ROOT / "analysis" / "private"
STORE.mkdir(parents=True, exist_ok=True)


def jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if p.exists() else []


def keep(src_dir: Path, sha: str) -> str | None:
    """Copy <sha>.* from a lane into the store (byte-verified); return the stored file name."""
    files = list((src_dir / "evidence").glob(f"{sha}.*"))
    if not files:
        return None
    dest = STORE / files[0].name
    if not dest.exists():
        shutil.copyfile(files[0], dest)
    if hashlib.sha256(dest.read_bytes()).hexdigest() != sha:
        raise SystemExit(f"stored copy of {sha} does not match its hash")
    return dest.name


final, sources = {}, []
for lane in sorted(LANES.glob("L*")):
    rnd = 2 if "r2_" in lane.name else 1
    for s in jl(lane / "sources.jsonl"):
        sources.append({**s, "lane": lane.name, "stored": keep(lane, s["sha256"])})
    review_dir = LANES / f"R_{lane.name}"
    reviews = {r["tie_id"]: r for r in jl(review_dir / "review.jsonl")}
    for s in jl(review_dir / "sources.jsonl"):
        sources.append({**s, "lane": review_dir.name, "stored": keep(review_dir, s["sha256"])})
    for v in jl(lane / "verdicts.jsonl"):
        tid = v["tie_id"]
        if tid in final and final[tid]["round"] > rnd:
            continue
        ev = [{**e, "file": keep(lane, e["sha256"])} for e in v.get("primary_evidence") or []]
        r = reviews.get(tid)
        new_ev = [{**e, "file": keep(review_dir, e["sha256"])} for e in (r or {}).get("new_evidence") or []]
        final[tid] = {
            "tie_id": tid, "lane_verdict": v["verdict"], "confidence": v.get("confidence"), "reason": v.get("reason"),
            "identity_basis": v.get("identity_basis"), "characterization_check": v.get("characterization_check"),
            "content_verdict": v.get("content_verdict"), "content_ref": v.get("content_ref"), "searched": v.get("searched"),
            "primary_evidence": ev, "lane": lane.name, "round": rnd, "rubric": v.get("rubric", "v1"),
            "review": None if r is None else {"agree": r["agree"], "proposed_verdict": r.get("proposed_verdict"),
                                               "issue": r.get("issue"), "new_evidence": new_ev},
        }

adj = {a["tie_id"]: a for a in jl(PRIVATE / "mb_adjudications.jsonl")}
todo = []
for tid, f in final.items():
    r = f["review"]
    if tid in adj:   # a written final-pass decision overrides, whether or not the review disagreed
        f["verdict"], f["status"], f["adjudication"] = adj[tid]["final_verdict"], "adjudicated", adj[tid]
    elif r is None:
        f["verdict"], f["status"] = f["lane_verdict"], "not_reviewed"
    elif r["agree"] or r.get("proposed_verdict") == f["lane_verdict"]:
        f["verdict"], f["status"] = f["lane_verdict"], "agreed" if r["agree"] else "agreed_with_note"
    else:
        f["verdict"], f["status"] = f["lane_verdict"], "disputed"
        todo.append({"tie_id": tid, "lane": f["lane"], "lane_verdict": f["lane_verdict"], "lane_reason": f["reason"],
                     "proposed_verdict": r.get("proposed_verdict"), "review_issue": r.get("issue")})

with (PRIVATE / "mb_verdicts.jsonl").open("w", encoding="utf-8") as out:
    for f in sorted(final.values(), key=lambda f: f["tie_id"]):
        out.write(json.dumps(f, ensure_ascii=False) + "\n")
with (PRIVATE / "mb_adjudication_todo.jsonl").open("w", encoding="utf-8") as out:
    for t in todo:
        out.write(json.dumps(t, ensure_ascii=False) + "\n")
with (PRIVATE / "mb_sources.jsonl").open("w", encoding="utf-8") as out:
    for s in sources:
        out.write(json.dumps(s, ensure_ascii=False) + "\n")
status = {}
for f in final.values():
    status[f["status"]] = status.get(f["status"], 0) + 1
print(f"ties with verdicts {len(final)} | {status} | sources {len(sources)} | stored files {len(list(STORE.iterdir()))}")
