"""Pull OpenFEC schedule E (independent expenditures) and schedule B (disbursements) for the pro-El-Sayed super PACs:
processed rows (keyset-paged), raw e-file rows, filings and report summaries. Key from env FEC_KEY (never printed).
Usage: FEC_KEY=... python3 -I scripts/fec_pull_spend.py <new out dir>   then scripts/mb_pac_spending.py <that dir>. Never overwrites."""
import json, os, sys, time, urllib.parse, urllib.request
KEY = os.environ["FEC_KEY"]; OUT = sys.argv[1]
def get(path, params):
    params = {**params, "api_key": KEY}
    url = "https://api.open.fec.gov/v1/" + path + "?" + urllib.parse.urlencode(params, doseq=True)
    for a in range(5):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            time.sleep(5 * (a + 1)); err = e
    raise RuntimeError(f"{path}: {type(err).__name__}")      # never echo the url (it carries the key)
def processed(sched, cid, extra):
    rows, last = [], {}
    while True:
        j = get(f"schedules/{sched}/", {"committee_id": cid, "per_page": 100, **extra, **last})
        rows += j["results"]
        li = j["pagination"].get("last_indexes")
        if not li or not j["results"]:
            return rows
        last = li
        time.sleep(0.4)
def efile(sched, cid):
    rows, page = [], 1
    while True:
        j = get(f"schedules/{sched}/efile/", {"committee_id": cid, "per_page": 100, "page": page})
        rows += j["results"]
        if page >= j["pagination"].get("pages", 1):
            return rows
        page += 1; time.sleep(0.4)
jobs = {"ffm_E": ("schedule_e", "C00919373", {"cycle": 2026}), "unity_E": ("schedule_e", "C00881011", {"cycle": 2026}),
        "ffm_B": ("schedule_b", "C00919373", {"two_year_transaction_period": 2026}),
        "unity_B": ("schedule_b", "C00881011", {"two_year_transaction_period": 2026})}
os.makedirs(OUT, exist_ok=True)
for name, (sched, cid, extra) in jobs.items():
    path = os.path.join(OUT, name + ".json")
    if os.path.exists(path):
        print(name, "exists, skipped", flush=True); continue
    p = processed(sched, cid, extra)
    e = efile(sched, cid)
    json.dump({"processed": p, "efile": e, "pulled_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, open(path + ".part", "w"))
    os.rename(path + ".part", path)
    print(name, "processed", len(p), "efile", len(e), flush=True)
# filings list for both committees (receipt dates, coverage ends, amendments)
for name, cid in (("ffm_filings_all", "C00919373"), ("unity_filings_all", "C00881011")):
    path = os.path.join(OUT, name + ".json")
    if not os.path.exists(path):
        rows, page = [], 1
        while True:
            j = get(f"committee/{cid}/filings/", {"per_page": 100, "page": page})
            rows += j["results"]
            if page >= j["pagination"].get("pages", 1):
                break
            page += 1
        json.dump(rows, open(path, "w"))
        print(name, len(rows), flush=True)
# report summaries (receipts, independent expenditures, operating costs, cash on hand per report)
for name, cid in (("ffm_reports", "C00919373"), ("unity_reports", "C00881011")):
    path = os.path.join(OUT, name + ".json")
    if not os.path.exists(path):
        rows, page = [], 1
        while True:
            j = get(f"committee/{cid}/reports/", {"per_page": 100, "page": page})
            rows += j["results"]
            if page >= j["pagination"].get("pages", 1):
                break
            page += 1
        json.dump(rows, open(path, "w"))
        print(name, len(rows), flush=True)
