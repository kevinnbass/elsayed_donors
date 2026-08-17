"""Recall pass over the 'ambiguous' name bucket.

Reclassifies only rows that nonwhite_name_share.bucket() left ambiguous,
using supplementary token lists curated from the top ~450 ambiguous
surnames by dollars plus a distinctive-first-name list for the tail.
Recovery is applied on all sides (Arab/Muslim, South Asian, Hispanic,
East Asian, AND Anglo/European) so the pass narrows uncertainty instead
of steering the shares. Writes analysis/name_share_recall.json.

Same caveats as the base classifier: name tokens, not a census.
"""
from __future__ import annotations

import importlib.util
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nonwhite_name_share", ROOT / "scripts" / "nonwhite_name_share.py"
)
nw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nw)

# --- Arab / Muslim / Persian / Turkish surnames missed by the base lists.
# South Asian Muslim names count as Muslim (repo convention), Levantine
# Christian surnames count as Arab (repo convention).
ARAB_MUSLIM_LAST_ADD = {
    # Arab / Levantine
    "SAREINI", "BAZZI", "BAZZY", "DERANI", "SHALABY", "SHALABI", "AYAD",
    "MAHSOUN", "SHABANEH", "SHWEHDI", "ABBARA", "ADRA", "KAAKEH", "BITTAR",
    "ZINEDDIN", "NOUNOU", "NEMER", "LOUTFI", "HAMARSHI", "QAWASMEH",
    "CHAIB", "ZALATIMO", "TAYIEM", "QUREINI", "BASHITI", "KRAYEM",
    "NADHIR", "OMAIRAT", "HADIDI", "GHANNAM", "FARHAT", "RABBAT",
    "JAHSHAN", "KANAAN", "SUKKAR", "SALMAN", "SHKOUKANI", "SHURBAJI",
    "KIBLAWI", "ATASSI", "KAZZIHA", "CHAMELLY", "KAMEL", "ODEH", "AYYASH",
    "FADLALLAH", "MASALKHI", "JABAJI", "MAHMALJY", "KASHAM", "ABDOLE",
    "ATEELI", "FADLI", "ITANI", "SULEIMAN", "SANKARI", "HACHEM",
    "HARARAH", "SABBAGH", "ABBASS", "FARDOUS", "MASKOUN", "DAHIR",
    "SABRI", "MORSY", "SIRAJELDIN", "TAKI", "RIMAWI", "TOMEH", "MUFTAH",
    "KADAH", "GINDY", "DABOUL", "REFAEI", "ZEITOUNEH", "HUSSEINI",
    "ALWAN", "KAYALI", "MURSHED", "SAEEDI", "YAHYA", "AKHRAS", "KHATEEB",
    "HARHASH", "KADRY", "MUNKARAH", "SAMMAN", "RASHAD", "AOSSEY", "KAYAT",
    "ABDALLA", "ETEER", "MSHAIEL", "FARAJ", "ASAD", "SEIKALY", "BARHOUM",
    "AMIN", "MATLOOB", "BATNIJI", "SABICELRAYESS", "JUNDISAMMAN",
    "BILTAGI", "SALKA", "BAGH", "HAMIDANI", "MOREB", "AKHTER",
    # Persian / Turkish
    "PARVIZ", "ASSEMI", "JAHROMI", "RAHNAMA", "SALIMI", "RAHMANI",
    "MOHEIMANI", "JAFARZADEH", "AKYUREK", "ZEYTUNCU", "LOTFI",
    # South Asian Muslim
    "AFTAB", "UMAIR", "YUNUS", "JAFFRI", "IMRAN", "CHOUDRY", "RIZWAN",
    "RAHAMAN", "MIAN", "BAWANEY", "MASKATIA", "MATIN", "QAZI", "IKRAM",
    "ARIF", "NIAZI", "KAZMI", "EHTESHAM", "RAZZAQUE", "WAHEED", "BASHEER",
    "IQBAL", "QADIR", "MAJEED", "SHAIQ", "KHALID", "HASHMI", "GHORI",
    "SHAHBAZ", "HANIF", "GORAYA", "MANSURI", "MAKHDOMI", "JAVAID",
    "SALEEM", "ULHAQ", "QUADRI", "HYDER", "ANJUM", "USMANI", "ABBASI",
    "KANJI", "SULTAN", "LOKHANDWALA", "BAQAI", "QARNI", "SHUTTARI",
    "JAMIL", "TAHIR", "HAQ", "MAROOF", "SHAREEF", "CHOWDHREY", "HUSSAINI",
    "KABIR", "ZUBAIRI", "MALLICK", "MURTUZA", "AAMIR", "JALISI", "VEHRA",
    "SALAHUDEEN", "BANDUKRA", "KYASA", "GHAZI", "MOTIWALA", "JAVID",
    "AZAD", "DALVI",
}

# Distinctive Arab / Muslim / Persian given names — strong single-token
# evidence; deliberately excludes cross-cultural names (Sara, Mona, Adam,
# Omer, Karma, Yara, Rani, Ramsey, Magda, Malek, Sam ...).
ARAB_MUSLIM_FIRST_ADD = {
    "GULNAZ", "RAHAF", "BAHAEDDIN", "TALAL", "RANIM", "BAKRI", "MAJED",
    "HAIDAR", "HAIDER", "RANDA", "MAJDI", "OUMAIMA", "HEBA", "HICHAM",
    "WAAD", "GEHAD", "MOHSIN", "NIZAR", "AZZAM", "ASAAD", "MUTTAA",
    "GHIATH", "MUAYAD", "HUTHAYFA", "AZEDDINE", "WAHED", "JIAB", "MARWA",
    "MOUHAMMED", "ABDUR", "JIHAD", "HAMZAH", "RAJAEI", "RAJAIE", "WADDAH",
    "TARIK", "SAHER", "YASSIR", "JUWARIA", "GHAZWAN", "FERDOUS", "RAFIL",
    "KARAM", "WAFA", "DIMA", "NAYEMA", "SUHAIR", "HASNAA", "BEENISH",
    "FAUZIA", "JIBRAN", "HILAL", "NAMEER", "FAZEL", "ABDULKADER",
    "JAWAD", "HUSNA", "NAVEED", "SULAIMAN", "KHALEEL", "SHAKEEL",
    "WALEED", "UMERAH", "REYAHD", "ZUBAID", "FIRAS", "MANIZA", "ZOHREEN",
    "OTHMAN", "OSAMAH", "MUJTABA", "KHAJA", "SHAHZAD", "MAHEEN", "AUSAF",
    "BASHAR", "LAITH", "SUHEB", "MOUSAB", "MOSAB", "NASHAT", "IRFAN",
    "SAIMA", "RIHAM", "FOAZ", "NAWAF", "AKIF", "ITEDAL", "FALEH",
    "GHALIB", "NEDDAL", "TAYYAB", "MUBASHAR", "NAZISH", "SONOBER",
    "AMRA", "NASHWAN", "MAZEN", "TAUQIR", "MISBAH", "TEHSEEN", "SAFA",
    "LATIFA", "LUTFUN", "SEHEL", "ZAHEER", "SHAZMA", "NAREMAN", "SAWEY",
    "OWAISE", "ALMECKDAD", "INJAMAMUL", "AZAM", "GHULAM", "HUNAID",
    "IHSAN", "CHAFEEK", "SALAHEDDINE", "ZAGLOUL", "SHERIF", "OMID",
    "URFI", "NURAIN", "MAHIR", "HABEEB", "ROBINA", "FAWAD", "MOINA",
    "DAINIA", "MAHMUNE", "INENHE", "SALEK", "FAYYAZ", "SCHARUKH",
    "ZAINA", "NIDA", "ABDALA", "BOUBEKEUR", "ANACE", "SUHEIL", "DEYAR",
    "FAHD", "ASIM", "RAMIKA", "EROL", "HANY",
}

SOUTH_ASIAN_LAST_ADD = {
    "MYLAVARAPU", "KALIYUR", "TEKCHANDANI", "KOMMAREDDI", "BEDI",
    "MAHAJAN", "SHETH", "LOHITSA", "SANGJI", "NAVAR", "DAHYA", "BHAIWALA",
}

EAST_ASIAN_LAST_ADD = {"KU", "RHEE"}

HISPANIC_LAST_ADD = {
    "RAMOSMONTIGNY", "ROLON", "ESPINOSA", "TOVAR", "DUARTE", "VERA",
    "TOROROMAN",
}

# Clear Anglo / European / Ashkenazi surnames the base list missed.
ANGLO_LAST_ADD = {
    "GRISWOLD", "KIDDER", "PLUMMER", "TRAVERS", "BRETSCHNEIDER",
    "WOODELL", "SOROS", "VIETOR", "POLONE", "KALT", "BOUCHER", "HANDEL",
    "LIPSON", "LOVETT", "STRAUS", "WORTHINGTON", "LUTZ", "CAUFIELD",
    "SUGARMAN", "COSTELLO", "HADDEN", "CUMMINS", "KATZ", "BOSCHERT",
    "SEYMOUR", "LEMIRE", "SALYER", "NAESS", "BUCCI", "HARKEMA", "PEARL",
    "SKRATEK", "STERLING", "MENDENHALL", "VETTER", "ABERLY", "GOMER",
    "MEDITCH", "VONSTEIN", "SEVERIN", "HOWSE", "STEWARD", "LAPOSTA",
    "LUPPINO", "COCCHIARELLA", "SCHMALE", "BRUELL", "MACLEOD", "LAKE",
    "GELMAN", "REDLICH", "MASSIE", "EWART", "GAFFNEY", "KEELER",
    "KILROY", "PAPPAS", "WELLER", "HAINES", "THIBAULT", "TOBIAS",
    "BRIGHAM", "KRUMPACK", "RANTZ", "STROHKIRCH", "SUTHERLAND",
    "SORTWELL", "CORPOLONGO", "FALVEY", "TOELLER", "ABRONS", "FALKOWSKI",
    "CITRON", "LAMPERTI", "HURWITZ", "THIEL", "FABBRI", "KRAUS",
    "WOOLLEY", "ZDRAVKOVSKA", "BLAUER", "BOLLINGER", "DISNEY", "HERSHEY",
    "EDEY", "ROUSSEAU", "AKERS", "HAMM", "HUSTED", "HOLSWORTH", "COZETTE",
    "VANHOUTEN", "LOWRY", "ERVINE", "CAPOZZOLI", "KEMENY", "POTTORFF",
    "HACKETT", "OCONNELL", "URBACH", "CATLIN", "GOODENOUGH", "YURK",
    "MCEVOY", "BURLEIGH", "KROHN", "SIMONS", "STETKEVYCH", "GEBALLE",
    "KETTLER", "CRARY", "STERN", "KAPLOWITZ", "NOVOTNY", "PINGREE",
    "STOREY", "SUESS", "BLIGHT", "VACKARO", "LOBEL", "VILLERS",
    "KRONNER", "TUTTLE", "SAMS", "DEJONG", "IESULAURO", "KOLLER", "PITT",
    "KILLEEN", "HAVERCRISSMAN", "COCKRELL", "KNOERLMORRILL", "PURDY",
    "SHERZER", "MCKEAN", "SUTFIN", "BARGER", "LANGER", "HOGE",
    "BARNHART", "LORD", "MACRAE", "POSAKONY", "MELROSE", "POLLACK",
    "TERWILLIGER", "RIESS", "VEITH", "PEITER", "HOARD", "GERMANN",
    "AARON", "BONIOR", "COVILLE", "COY", "KONTRY", "KORNBLUH", "SHEA",
    "ZIEWACZ", "LEAF", "BOHLKE", "KLINGENBERGER", "DUGGAN", "MOOTY",
    "MARLEEN", "BESMAN", "CHELOFF",
}


def recall_bucket(name: str) -> str | None:
    """Supplementary classification for a base-ambiguous row, or None."""
    last, first = nw.last_first(name)
    last_parts = set(last.replace("-", " ").split()) | {last}
    if last_parts & ARAB_MUSLIM_LAST_ADD:
        return "arab_or_muslim"
    if first in ARAB_MUSLIM_FIRST_ADD:
        return "arab_or_muslim"
    if last_parts & SOUTH_ASIAN_LAST_ADD:
        return "south_asian"
    if last_parts & EAST_ASIAN_LAST_ADD:
        return "east_asian"
    if last_parts & HISPANIC_LAST_ADD:
        return "hispanic_latino"
    if last_parts & ANGLO_LAST_ADD:
        return "anglo_white"
    return None


def main() -> None:
    gift = defaultdict(lambda: {"n": 0, "amt": 0.0})
    recovered = defaultdict(lambda: {"n": 0, "amt": 0.0})
    tot = 0.0
    roster = ROOT / "analysis" / "roster_named_itemized.jsonl"
    with roster.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            tot += r["amt"]
            b = nw.bucket(r.get("name") or "")
            if b == "ambiguous":
                rb = recall_bucket(r.get("name") or "")
                if rb is not None:
                    recovered[rb]["n"] += 1
                    recovered[rb]["amt"] += r["amt"]
                    b = rb
            gift[b]["n"] += 1
            gift[b]["amt"] += r["amt"]

    nonwhite = sum(
        gift[k]["amt"]
        for k in ("arab_or_muslim", "levantine_mena", "hispanic_latino",
                  "south_asian", "east_asian", "african_distinctive")
    )
    arab_muslim = gift["arab_or_muslim"]["amt"] + gift["levantine_mena"]["amt"]

    def cut(amt: float, n: int | None = None) -> dict:
        d = {"amt": round(amt, 2), "pct": round(100.0 * amt / tot, 1)}
        if n is not None:
            d["n_gifts"] = n
        return d

    out = {
        "named_itemized_total": round(tot, 2),
        "method": (
            "Base classifier from nonwhite_name_share.py, then a recall pass "
            "over its ambiguous bucket using supplementary token lists "
            "curated from the top ~450 ambiguous surnames by dollars plus a "
            "distinctive-given-name list. Recovery applied to all buckets "
            "(Anglo/European included), only to base-ambiguous rows. "
            "Name tokens, not a religion or race census."
        ),
        "arab_or_muslim_incl_levantine": cut(
            arab_muslim,
            gift["arab_or_muslim"]["n"] + gift["levantine_mena"]["n"],
        ),
        "nonwhite_coded": cut(nonwhite),
        "anglo_white_coded": cut(gift["anglo_white"]["amt"], gift["anglo_white"]["n"]),
        "ambiguous_remaining": cut(gift["ambiguous"]["amt"], gift["ambiguous"]["n"]),
        "recovered_from_ambiguous": {
            k: {"amt": round(v["amt"], 2), "n_gifts": v["n"]}
            for k, v in sorted(recovered.items(), key=lambda kv: -kv[1]["amt"])
        },
        "by_bucket": {
            k: cut(v["amt"], v["n"])
            for k, v in sorted(gift.items(), key=lambda kv: -kv[1]["amt"])
        },
    }
    dest = ROOT / "analysis" / "name_share_recall.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k != "by_bucket"}, indent=2))
    print("WROTE", dest)


if __name__ == "__main__":
    main()
