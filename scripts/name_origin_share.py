"""Arab-or-Muslim-coded share of named dollars from a validated name-origin lexicon (2026-10 pass).

Inputs
  analysis/name_lexicon/surnames.jsonl, given.jsonl  token -> origin, p_am (probability the name, as
      borne by this donor list, is Arab-or-Muslim-coded), conf, shared.  Built by LLM labelling against
      a fixed rubric (analysis/name_lexicon/RUBRIC.md) and scored on a Wikipedia name-category gold
      set before use (analysis/name_lexicon/validation.json).
  analysis/private/name_pairs.jsonl (optional, not committed)  full-name judgments for pairs whose
      tokens are uncertain or shared; overrides the token combination for those pairs.

Per gift, p = the pair judgment if there is one, else max(p_last, p_first) as the low reading and
1 - (1 - p_last)(1 - p_first) as the high one (the two tokens are positively correlated, so the
truth lies between); the point estimate uses their mean. Same convention as before: a name counts
when either the surname or the given name is Arab-or-Muslim-coded, any religion.

Writes analysis/name_origin_share.json (aggregates only).
"""
from __future__ import annotations

import importlib.util
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEX = ROOT / "analysis" / "name_lexicon"
PAIRS = ROOT / "analysis" / "private" / "name_pairs.jsonl"
OUT = ROOT / "analysis" / "name_origin_share.json"
PRIMARY_CUTOFF = "20260715"  # last day of the pre-primary report
CONFIDENT = 0.9
AM_ORIGINS = {"ARABIC", "PERSIAN", "TURKISH", "SOUTH_ASIAN_MUSLIM", "AFGHAN_PASHTO", "SOMALI_EAST_AFRICAN_MUSLIM",
              "WEST_AFRICAN_MUSLIM", "BALKAN_MUSLIM", "SOUTHEAST_ASIAN_MUSLIM", "OTHER_MUSLIM"}

spec = importlib.util.spec_from_file_location("mus", ROOT / "scripts" / "muslim_name_share.py")
mus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mus)


def load_lexicon(name: str) -> dict:
    out = {}
    with (LEX / name).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                out[r["token"]] = r
    return out


def tokens(name: str) -> tuple[str, str]:
    last, first = mus.tokens(name)
    return last.replace(" ", ""), first


def main() -> None:
    sur, giv = load_lexicon("surnames.jsonl"), load_lexicon("given.jsonl")
    # final-pass audit corrections (each with a written reason)
    for line in (LEX / "audit_overrides.jsonl").open(encoding="utf-8"):
        if line.strip():
            o = json.loads(line)
            target = sur if o["kind"] == "surname" else giv
            target[o["token"]] = {**target.get(o["token"], {}), "token": o["token"], "p_am": o["p_am"], "origin": o["origin"]}
    pairs = {}
    if PAIRS.exists():
        for line in PAIRS.open(encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                pairs[(r["last"], r["first"])] = r

    def judge(name: str) -> dict:
        last, first = tokens(name)
        # an initial or one-letter token carries no origin information
        ls = sur.get(last) if len(last) > 1 else None
        gs = giv.get(first) if len(first) > 1 else None
        pl = ls["p_am"] if ls else 0.0
        pf = gs["p_am"] if gs else 0.0
        lo, hi = max(pl, pf), 1 - (1 - pl) * (1 - pf)
        origin = ls["origin"] if ls and pl >= pf else (gs["origin"] if gs else "UNKNOWN")
        other_origin = (ls or gs or {}).get("origin", "UNKNOWN")  # where the non-AM share of the name points
        which = ("both" if pl >= 0.5 and pf >= 0.5 else "last_only" if pl >= 0.5
                 else "first_only" if pf >= 0.5 else "neither")
        pr = pairs.get((last, first))
        if pr:
            lo = hi = pr["p_am"]
            origin = pr.get("origin", origin)
        return {"lo": lo, "hi": hi, "p": (lo + hi) / 2, "origin": origin, "which": which, "other_origin": other_origin,
                "labelled": bool(ls or gs), "pair": bool(pr)}

    roster = [json.loads(line) for line in (ROOT / "analysis" / "roster_named_itemized.jsonl").open(encoding="utf-8")]
    tot = sum(r["amt"] for r in roster)
    acc = defaultdict(lambda: defaultdict(float))
    for r in roster:
        j = judge(r["name"])
        a = r["amt"]
        cuts = {
            "all": "all",
            "period": "through_jul15" if r["date"] <= PRIMARY_CUTOFF else "jul16_sep30",
            "state": "MI" if r["state"] == "MI" else "outside_MI",
        }
        for dim, val in cuts.items():
            d = acc[(dim, val)]
            d["amt"] += a
            d["n"] += 1
            d["exp"] += a * j["p"]
            d["lo"] += a * j["lo"]
            d["hi"] += a * j["hi"]
            d["confident_am"] += a * (j["lo"] >= CONFIDENT)
            d["confident_not"] += a * (j["hi"] <= 1 - CONFIDENT)
            d["n_am_exp"] += j["p"]
        acc[("origin", j["origin"] if j["origin"] in AM_ORIGINS else "uncertain residual (non-AM origin)")]["exp"] += a * j["p"]
        acc[("which", j["which"])]["exp"] += a * j["p"]
        acc[("non_am_origin", j["other_origin"] if j["other_origin"] not in AM_ORIGINS else "AM-origin token, non-AM pair")]["exp"] += a * (1 - j["p"])
        acc[("coverage", "labelled" if j["labelled"] else "unlabelled")]["amt"] += a
        acc[("coverage", "pair_judged")]["amt"] += a * j["pair"]

    def cut(d: dict, base: float) -> dict:
        return {
            "amt": round(d["amt"], 2), "n_gifts": int(d["n"]),
            "expected_pct": round(100 * d["exp"] / base, 1),
            "low_pct": round(100 * d["lo"] / base, 1), "high_pct": round(100 * d["hi"] / base, 1),
            "confident_am_pct": round(100 * d["confident_am"] / base, 1),
            "confident_not_am_pct": round(100 * d["confident_not"] / base, 1),
            "uncertain_pct": round(100 * (d["amt"] - d["confident_am"] - d["confident_not"]) / base, 1),
            "expected_gift_share_pct": round(100 * d["n_am_exp"] / d["n"], 1) if d["n"] else None,
        }

    out = {
        "named_itemized_total": round(tot, 2),
        "method": __doc__.strip().split("\n\n")[0],
        "all": cut(acc[("all", "all")], tot),
        "by_period": {v: cut(acc[("period", v)], acc[("period", v)]["amt"])
                      for v in ("through_jul15", "jul16_sep30")},
        "by_state": {v: cut(acc[("state", v)], acc[("state", v)]["amt"]) for v in ("MI", "outside_MI")},
        "by_origin_expected_pct": {k[1]: round(100 * v["exp"] / tot, 2)
                                   for k, v in sorted(acc.items(), key=lambda kv: -kv[1]["exp"])
                                   if k[0] == "origin" and v["exp"] >= 0.0005 * tot},
        "by_token_expected_pct": {k[1]: round(100 * v["exp"] / tot, 2) for k, v in acc.items() if k[0] == "which"},
        "non_am_by_origin_expected_pct": {k[1]: round(100 * v["exp"] / tot, 2)
                                          for k, v in sorted(acc.items(), key=lambda kv: -kv[1]["exp"])
                                          if k[0] == "non_am_origin" and v["exp"] >= 0.0005 * tot},
        "coverage": {k[1]: round(100 * v["amt"] / tot, 2) for k, v in acc.items() if k[0] == "coverage"},
    }

    donors = [json.loads(line) for line in (ROOT / "analysis" / "donors_net.jsonl").open(encoding="utf-8")]
    top = json.loads((ROOT / "analysis" / "top_donors.json").read_text(encoding="utf-8"))
    key = lambda d: (d["last_norm"], d["first_norm"], d["suffix"], d["zip5"], d["house"])
    sample = {key(d) for d in top["top100_random_from_cap"]["donors"]}
    tiers = {"all_donors": donors, "at_7000_max": [d for d in donors if d["net"] >= 6999.995],
             "joint_committee_only_donors": [d for d in donors if d["n_gifts"] == 0 and d["joint_committee"] > 0],
             "random_top100": [d for d in donors if key(d) in sample]}
    net_all = sum(d["net"] for d in donors)
    out["by_donor_tier"] = {}
    for name, ds in tiers.items():
        js = [judge(d["name"]) for d in ds]
        net = sum(d["net"] for d in ds)
        out["by_donor_tier"][name] = {
            "n_donors": len(ds),
            "expected_pct_of_donors": round(100 * sum(j["p"] for j in js) / len(ds), 1),
            "expected_pct_of_net_dollars": round(100 * sum(j["p"] * d["net"] for j, d in zip(js, ds)) / net, 1),
            "tier_pct_of_all_net": round(100 * net / net_all, 1),
        }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("all", "by_period", "by_state", "coverage")}, indent=1))


if __name__ == "__main__":
    main()
