"""Share of named-itemized $ from donors whose names look Arab or Muslim.

Arab Christian / Levantine surnames count. So do Muslim names that are
not Arab (Urdu, Persian, Turkish, Afghan). Not a religion or ethnicity census.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "analysis" / "roster_named_itemized.jsonl"

# Distinctive given names (Arabic / Persian / Turkish / common Muslim use).
# Keep out highly ambiguous Western tokens (Adam, Mary, Sarah as-only).
FIRST = {
    "ABDUL", "ABDULLAH", "ABDULLA", "ABDEL", "ABDALLA", "ABDALLAH",
    "ABDIRAHMAN", "ABDIRAHMAN", "ABDULRAHMAN", "ABDULRAHMAN", "ABDULRAHMAN",
    "AHMAD", "AHMED", "AHMET", "AKEEM", "AKRAM", "ALI", "ALAA", "ALAAEDDIN",
    "AMINA", "AMINAH", "AMIN", "AMIRA", "AMIR", "ANWAR", "AYESHA", "AISHA",
    "AYSHA", "AZIZ", "AZIZA",
    "BASIL", "BILAL", "BUSHRA",
    "DALIA", "DAWOOD", "DAUD",
    "FADIA", "FAHAD", "FAISAL", "FARAH", "FARID", "FARIDA", "FATIMA", "FATIMAH",
    "FATMA", "FAYEZ", "FIROZ",
    "HABIBA", "HADI", "HAIFAA", "HAJAR", "HAMID", "HAMZA", "HANA", "HANAN",
    "HANI", "HASAN", "HASSAN", "HATEM", "HAYTHAM", "HESHAM", "HISHAM",
    "HUSAIN", "HUSAYN", "HUSSEIN", "HUSSAIN",
    "IBRAHIM", "IDRIS", "ILYAS", "IMAD", "IMAN", "IMRAN", "ISMAIL", "ISMAEEL",
    "JAMAL", "JAMEEL", "JAMILA",
    "KAMAL", "KARIM", "KHADIJA", "KHADIJA", "KHALED", "KHALID", "KHALIL",
    "LAYLA", "LEILA",
    "MAHDI", "MAHMOUD", "MAHMUD", "MAJID", "MALIK", "MARIAM", "MARYAM",
    "MOHAMAD", "MOHAMED", "MOHAMMAD", "MOHAMMED", "MOSTAFA", "MUSTAFA",
    "MUHAMMAD", "MUHAMMED", "MUNA", "MUNIR", "MUSAB", "MUZAMMIL",
    "NADIA", "NADIR", "NAJIB", "NASIR", "NASREEN", "NOOR", "NOURA", "NUR",
    "OMAR", "OMAR", "OSAMA", "OUSAMA",
    "QASIM",
    "RABIA", "RAFIQ", "RAHIM", "RAMI", "RAMZI", "RASHA", "RASHID", "REEM",
    "RIAZ", "RIDWAN",
    "SAAD", "SABAH", "SADIA", "SAEED", "SAID", "SAIF", "SALAH", "SALEH",
    "SALIM", "SALMA", "SALMAN", "SAMIR", "SAMIRA", "SANA", "SAWSAN",
    "SHADIA", "SHAFIQ", "SHAHID", "SHIRIN", "SUHAIL", "SULTAN", "SUMAYA",
    "TAHA", "TAHER", "TARIQ", "TAYEB",
    "USAMA", "USMAN",
    "WAEL", "WAHID", "WALID", "WISAM",
    "YAHYA", "YASIR", "YASMIN", "YASMINE", "YOUSSEF", "YOUSEF", "YUSUF",
    "ZAHRA", "ZAID", "ZAIN", "ZAINAB", "ZAKARIA", "ZAKI", "ZAYD", "ZEINAB",
    "ZUBAIR",
    # additional high-frequency in this roster (from El-Sayed MI/Arab-American set)
    "ABDULRAHMAN", "ABDUALRAHMAN", "ADHAM", "AMANI", "ASHRAF", "AYMAN",
    "BASIM", "FAWZI", "GHASSAN", "HAITHAM", "HATEM", "HAZIM", "HUSAM",
    "ILTEFAT", "ISSA", "JAMIL", "KAMEL", "LOAY", "MAEN", "MAGED", "MAZEN",
    "MOHD", "NADEEM", "NAJAH", "NASEEM", "NAZEEH", "OSAMA", "RAED", "RAMY",
    "REEHAN", "SADEK", "SAMEH", "SHADI", "SULEMAN", "SYED", "TAREK",
    "USAMA", "WAEL", "YAMAAN", "ZEIN", "ZUHAIR", "FARIHA", "HAIFAA",
    "MADA", "MARJAN", "RAFIA", "RUSHDI",
    "ANAS", "ISLAM", "AIMAN", "FERAS", "SHEREEF", "SHARIF", "SHAREEF",
    "MUFID", "YUSRA", "YOUSRA", "AMER", "AMRO", "ISMAEL",
    "HUSSIEN", "SENAN", "MEHAK", "MOEZ", "MERAJ",
    "ABDALMAJID", "ZEAD", "ZIAD", "ZIYAD", "MANNAN",
    "RUDAH", "TARICK", "QUAID",
    "SAMEER", "MOHSEN", "AALIYA", "WASIM", "MAHJABEEN",
    "GHADA", "HAZEM", "AMR", "IRSHAD", "MAZHAR", "RIYAZ", "RACHA",
    # roster misses (high-dollar El-Sayed itemized names)
    "AMMAR", "KASHIF", "NABIL", "KAMRAN", "REHAN", "JUNAID", "SAMER",
    "IHAB", "TALHA", "NAWAL", "HASEEB", "AYMEN", "AYMAN", "MUIZZ",
    "HAROON", "OUSSAMA", "YOUSUF", "SALEEM", "MARWAN", "NABEEL",
    "WASEEM", "SAQIB", "AJMAL", "AAMIR", "MUSAAB", "FARAZ", "NABEELA",
    "HIBA", "MAHA", "MANAL", "RANIA", "ZENAIB", "FAIZIYA", "EYAS",
    "ZAHER", "AYEZA", "MUWAFFAK", "ZAHIDA", "SHUAIB", "SHIREIF",
    "SAMAR", "FAHEEM", "MURTAZA", "KHURRAM", "WASFI", "SAEB",
    "ARSHAD", "ATA", "HADIA", "ANEES", "NAUSHEEN", "SAADIA",
    "SHAHRZAD", "KASSEM", "FADI", "ARIEGE", "SELMA", "KOMWANEE",
    "NAWWAF", "HADEAL", "BASSAM", "MAJD", "SHAHZEB", "SAJJAD",
    "SAHAR", "NAGLA", "MUNZER", "UMBREEN", "AKHTER", "SAFWAN",
    "FADWA", "KIRIN", "HADIA", "RAJA", "ROWNAK", "EJAZ", "ZAEN",
    "SIKANDAR", "AMANA", "ZENOBIA", "HOME", "FAREED", "RAAFAY",
    "NADEEN", "AYA", "SHUMAILA", "HADIA", "BASEL", "SAMEENA",
    "MASOOD", "SHARIQ", "AZEDINE", "SHAINA", "FAROOQ",
    "ZAHID", "ISSAM", "LAMA", "GHAITH", "HAKEEM", "FAROUK",
    "TALIB", "DILARA", "YASER", "LANA", "BURHAN", "TALA",
    "ASIF", "ESAM", "ADNAN", "EMAD", "SAMIA", "NASSER",
    "NASER", "ABEDEL", "JAD", "DILNAZ", "ALY", "MOJAHED",
    "LAILA", "FARHAAD", "MOHANNAD", "FAWZIA", "HASSANE",
    "FARHAN", "ZAED", "MUBEEN", "MAHER", "NIMAN", "EHTISHAM",
    "ALLAEDDIN", "KENAZ", "ANASIE", "JAUWAAD", "HASEENA",
    "ADEEL", "MUMTAZ", "ZAFIR", "ABIR", "RHAMI", "HEBBA",
    "SAGHEER", "BABUR", "RAZAN", "NUZHAT", "HUMA", "HOSSAM",
    "SHAHEENA", "ARWA", "UZMA", "SHAMA", "MAZIN", "AMAN",
    "MANSOUR", "SHAARIQ", "ZESHAN", "SHABBIR", "HASSON",
    "ABED", "ABID", "SINAN", "MOHEEB", "MUHEEB", "ZEINA",
    "ZEYNA", "REHANA", "MAYSAA", "MAYSA", "SIDRA", "SIDRAH",
    "SHAHED", "SHAHEDOLLA", "MUNTHER", "MONEER", "LEENA",
    "MAYSAA", "RIMA",
    "ELIAS", "BOUTROS", "BUTROS", "MAROUN", "GIRGIS", "GUIRGUIS",
}

# Surnames strongly associated with Muslim / Arab / Afghan / Pakistani naming.
# Exclude ultra-generic if they collide hard (LEE, SHAH alone is borderline).
LAST = {
    "ABBAS", "ABDALLAH", "ABDEL", "ABDUL", "ABDULLAH", "ABOU", "ABU",
    "AHMAD", "AHMED", "AKHTAR", "AKTAR", "ALAMI", "ALI", "ALAM",
    "ANSARI", "ARAIN", "ASLAM", "AWAD", "AYOUB", "AZIZ",
    "BAGHDADI", "BAIG", "BARAKAT", "BASHIR", "BASSI",
    "CHAUDHRY", "CHAUDHARY", "CHOWDHARY", "CHOWDHURY",
    "DARWISH", "DAWOOD",
    "ELSAYED", "EL-SAYED", "ELSAYED",
    "FARAH", "FAROOQ", "FAROOQI",
    "GHANI", "GHAZAL",
    "HABIB", "HADI", "HAIDAR", "HAJJAR", "HAKIM", "HAMAD", "HAMDAN",
    "HAMID", "HAMZA", "HAROON", "HASAN", "HASSAN", "HUSAIN", "HUSSEIN",
    "HUSSAIN",
    "IBRAHIM", "ISMAIL", "ISSA", "ISSAWI",
    "JABER", "JABARA", "JAMAL", "JAVED",
    "KAMAL", "KARIM", "KHALIL", "KHAN",
    "MAHMOUD", "MAHMOOD", "MALIK", "MANSOUR", "MASRI", "MOHAMED",
    "MOHAMMAD", "MOHAMMED", "MUSTAFA",
    "NASSER", "NASEER", "NASIR", "NOOR", "SHAMSI", "MEMON", "YAQUB",
    "OMAR", "OSMAN",
    "QURESHI",
    "RAHMAN", "RAHIM", "RASHID", "RIZVI", "RIZK",
    "SAAD", "SALEH", "SALIM", "SHAH", "SHAIKH", "SHEIKH", "SIDDIQUI",
    "SYED",
    "TAHA", "TARIQ",
    "YOUSSEF", "YOUSEF",
    "ZAHRA", "ZAKARIA", "ZAMAN",
    # high-dollar roster surnames already reviewed as Arab/Muslim-coded
    "ABAZA", "ABOUNASSIF", "ABUNASRA", "ABUMUSTAFA", "ALMADANI",
    "ALNAJJAR", "ALWATTAR", "ALGHANEM", "ALAMERI", "AL-AMERI",
    "ELNABTITY", "ELBANNA", "ELDAWY", "EZZEDDINE",
    "FURRHA", "HAMZAVI", "HILALY", "JONDY",
    "KHALAF", "KURDI", "MOAMMAR", "MOKHTARZADA", "MOHAMMADI",
    "MOSSA", "MOSSA-BASHA", "NAFAL", "OBEID", "PERACHA", "PERACHA-RIYAZ",
    "SAADEH", "SAFADI", "SAJJAD", "SHAHROUR", "SHALLAL",
    "ALJUMAILY", "GHAYASUDDIN", "MOHIUDDIN", "RAMADAN", "ZUGHAYER",
    "ELSIESY", "AKEEL", "GOMAA", "KATRANJI", "EBRAHIM", "SAIFEE",
    "MOSA-BASHA", "MOSSABASHA", "KABAKIBO", "AFANEH", "SAIFAN",
    "RAZZAK", "SAGHIR", "GAMAY",
    # roster last-name misses (Muslim/Arabic/Urdu/Persian-coded; not Levantine Christian)
    "RASHEED", "ZAIDI", "SARDAR", "KAZI", "SIDDIQI", "SIDDIQUE",
    "ALVI", "TAYEB", "AHSAN", "ZIA", "JUKAKU", "SHAMEEM", "ISLAM",
    "REHMAN", "MOHSIN", "SOLIMAN", "RAZA", "MASOOD", "HAMMOUD",
    "BADR", "SAEED", "MUBARAK", "BHATTI", "SATTAR", "HAFEEZ",
    "KHATIB", "RAZVI", "ZAHURULLAH", "KHWAJA", "MEDHKOUR", "ZAFAR",
    "SARSOUR", "HAQUE", "AZHAR", "ABDULHAK", "FETOUH", "HAMEED",
    "AKBAR", "MOUSTAFA", "MOZAFFAR", "HOSEIN", "RAFIQUE", "NAWAZ",
    "DAKHLALLAH", "MUSHEINESH", "SHABEEB", "KHIRFAN", "GAZIANI",
    "TARAKJI", "ABDEEN", "ABED", "MAALI", "KENAWY", "KETTANJI",
    "MEZOUI", "AZZAWI", "HAMOUI", "BARGHOUTI", "KAUKAB", "TABASSUM",
    "ATTARAS", "TAMEEZ", "BDAIR", "SAID", "MIR", "KOLA",
    "HOSSAIN", "MINHAS", "SHARIFF", "MUSMAR", "SHAKIR",
    "SHUKAIRY", "ASHAI", "ABBASSI", "JALLAD", "JANDALI",
    "BAKDASH", "SAYEED", "TAYYEN", "DWEIK", "MUSBA", "FAWAZ",
    "MIRZA", "GHANAYEM", "WARAICH", "JILANI", "CHEEMA",
    "LARI", "WANI", "FAREED", "KHORFAN", "AZEEM", "SHEHADA",
    "AREF", "CHOHAN", "MUNIR", "HAFEZ", "BEYDOUN", "OMEISH",
    "SIDDIQEE", "LATEEF", "ASBAHI", "SALAM", "SOOFI", "IJAZ",
    "METWALLY", "ABEDIN", "HIJAZI", "KHAJA", "TOTONJI",
    "HUMAYUN", "HAIDER", "FAROUKI", "AMINZAY", "SAMADPOUR",
    "QURAISHI", "LATIF", "RIYAZ", "BAYDOUN", "DWAIK", "HUQ",
    "JAWAD", "SAWANI", "MOUAYAD", "CHANDA", "KAPASI",
    "KOTHAWALA", "HANDOO", "YILDIZ",
    "DAOUD", "MOLLA", "SALEM", "BASHA",
}

# Arab / Levantine surnames used by Christians and Muslims. Headline cut is
# "Arab or Muslim" so these count even when the family is typically Christian.
ARAB_LAST = {
    "HADDAD", "KHOURY", "KHOURI", "ELKHOURY", "ABDO", "ABDOU", "ABDULAHAD",
    "CHAMI", "DUDUM", "FREIJ", "SHEHADI", "SHEHADEH", "AZAR", "BATTAT",
    "MUALLEM", "HABAYEB", "FAKHOURY", "FAKHORY", "HARAJLI", "ALO",
    "SHAHBANDAR", "SIAM", "ANDONI", "HOMSI", "SHAMI", "TARAZI",
    "HOURANI", "NASSAR", "NASR", "SABAGH", "DAYE", "BISHARAT",
    "SAROFIM", "SINNO", "SARAFA", "SALIBA", "MALOUF", "MAALOUF",
    "TOHME", "TOHMEH", "GEHA", "HAGE", "BOUTROS", "BUTROS",
    "GIRGIS", "GUIRGUIS", "MIKHAEL", "MIKHAIL", "HANNA",
    "NAJJAR", "NAJAR", "KASSAB", "KASSIS", "SAMAAN", "SEMAAN",
    "NADER", "NAYFEH", "SAYEGH", "SAYEG", "TUMMA", "TOUMA",
}

# prefixes on last or first
PREFIX = re.compile(
    r"^(ABDUL|ABDEL|ABDALLAH|ABDULLAH|ABDI|ABU|AL|EL|BIN|BINT|UDDIN|UDDIN)\b"
    r"|^(EL|AL)[- ]",
    re.I,
)

# last-name particles
LAST_PREFIX = re.compile(r"^(EL|AL|ABDUL|ABDEL|ABU)[- ]", re.I)

# drop known non-matches that collide
LAST_EXCLUDE = {"JURVETSON", "TURK", "ROSS", "CONNELL", "KOKORIS", "JIMENEZ", "AUERBACH"}
# Turk as surname can be Armenian/Turkish secular - keep as weak only
FIRST_EXCLUDE = {"ANDY", "WILLIAM", "STEVE", "LYNDSEY", "KARLA", "KATHLEEN", "MICHAEL"}


def tokens(name: str) -> tuple[str, str]:
    name = (name or "").strip()
    if "," in name:
        last, rest = name.split(",", 1)
    else:
        parts = name.split()
        last, rest = (parts[-1] if parts else ""), " ".join(parts[:-1])
    last_n = re.sub(r"[^A-Z]+", " ", last.upper()).strip()
    first_n = re.sub(r"[^A-Z]+", " ", rest.upper()).strip().split()
    first_tok = first_n[0] if first_n else ""
    return last_n, first_tok


def classify(name: str) -> str:
    last, first = tokens(name)
    last_key = last.replace(" ", "-")
    last_compact = last.replace(" ", "")
    if first in FIRST_EXCLUDE:
        first_hit = False
    else:
        first_hit = first in FIRST or bool(PREFIX.match(first))
    if last_compact in LAST_EXCLUDE or last_key in LAST_EXCLUDE:
        last_hit = False
    else:
        last_hit = (
            last_key in LAST
            or last_compact in LAST
            or last in LAST
            or last_key in ARAB_LAST
            or last_compact in ARAB_LAST
            or last in ARAB_LAST
            or bool(LAST_PREFIX.match(last))
            or any(p in LAST or p in ARAB_LAST for p in last.split())
        )
        # El-X / Al-X (spaced, hyphenated, or concatenated Elmasry)
        if re.match(r"^(EL|AL) ", last) or re.match(r"^(EL|AL)-", last_key):
            last_hit = True
        compact = last.replace(" ", "")
        western_al_el = {
            "ALLEN", "ALBERT", "ALDRICH", "ALEXANDER", "ALVAREZ", "ALONSO",
            "ALFORD", "ALTON", "ELLIS", "ELDER", "ELKINS", "ELLIOTT",
            "ELMORE", "ELSON", "ELTON", "ELWOOD", "ELMAN",
        }
        if re.match(r"^(EL|AL)[A-Z]{4,}$", compact) and compact not in western_al_el:
            last_hit = True
        # concatenated Abdulhak / Abdelrahman (hyphen/space form already in LAST_PREFIX)
        if re.match(r"^(ABDUL|ABDEL|ABDALLAH|ABDULLAH|ABDI)", compact):
            last_hit = True
        # Abutaa / Abousaleh / Abuzaakouk — ABU/ABOU plus at least 2 more letters
        if re.match(r"^(ABU|ABOU)[A-Z]{2,}$", compact):
            last_hit = True
        if re.search(r"(ULLAH|UDDIN|UZZAMAN)$", compact):
            last_hit = True
    if first_hit and last_hit:
        return "both"
    if first_hit:
        return "first_only"
    if last_hit:
        return "last_only"
    return "no"


def main() -> None:
    gift = defaultdict(lambda: {"n": 0, "amt": 0.0})
    donors = defaultdict(lambda: {"amt": 0.0, "n": 0, "name": "", "cls": ""})
    tot = 0.0
    with ROSTER.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            tot += r["amt"]
            cls = classify(r.get("name") or "")
            gift[cls]["n"] += 1
            gift[cls]["amt"] += r["amt"]
            k = (r.get("last_norm"), r.get("first_norm"))
            d = donors[k]
            d["amt"] += r["amt"]
            d["n"] += 1
            d["name"] = r.get("name") or ""
            d["cls"] = cls

    any_amt = gift["both"]["amt"] + gift["first_only"]["amt"] + gift["last_only"]["amt"]
    strong_amt = gift["both"]["amt"]
    out = {
        "named_itemized_total": round(tot, 2),
        "label": "arab_or_muslim",
        "method": (
            "Token match on FEC name against Arab-or-Muslim name lists: "
            "Arabic / Persian / Urdu / Turkish given names and surnames, "
            "Abdul-/El-/Al-/Abu- prefixes, AND Levantine/Arab Christian "
            "surnames (Haddad, Khoury, Abdo, Chami, Dudum, Boutros, Girgis). "
            "Pakistani/Bangladeshi/Persian Muslim names count (Muslim, not "
            "necessarily Arab). Levantine Christians count (Arab, not "
            "necessarily Muslim). Not a religion or ethnicity census. "
            "False positives (Ali, Khan, Shah, Hanna) and false negatives "
            "(converts, fully Anglicized names) both exist."
        ),
        "any_name_token": {
            "amt": round(any_amt, 2),
            "pct": round(100.0 * any_amt / tot, 1),
            "n_gifts": gift["both"]["n"] + gift["first_only"]["n"] + gift["last_only"]["n"],
        },
        "both_first_and_last": {
            "amt": round(strong_amt, 2),
            "pct": round(100.0 * strong_amt / tot, 1),
            "n_gifts": gift["both"]["n"],
        },
        "by_class": {
            k: {"amt": round(v["amt"], 2), "n_gifts": v["n"],
                "pct": round(100.0 * v["amt"] / tot, 1)}
            for k, v in gift.items()
        },
        "top20_any": [
            {"name": d["name"], "amt": round(d["amt"], 2), "class": d["cls"]}
            for d in sorted(
                (x for x in donors.values() if x["cls"] != "no"),
                key=lambda x: -x["amt"],
            )[:20]
        ],
    }
    dest = ROOT / "analysis" / "muslim_name_share.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k != "top20_any"}, indent=2))
    print("\nTop 20 any-token")
    for r in out["top20_any"]:
        print(f"  {r['name']} — ${r['amt']:,.0f} — {r['class']}")
    print("WROTE", dest)


if __name__ == "__main__":
    main()
