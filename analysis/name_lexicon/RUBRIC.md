# Name-origin labeling rubric, v1

You label **name tokens** (one surname or one given name per line) from a list of U.S. political donors.
Each input line is tab-separated: the token (upper case, spaces and hyphens removed), then context.
For a surname the context is: the spelling as filed, the given names most often seen with it in this
donor list, the top states, and the number of gifts. For a given name: the surnames most often seen
with it, the top states, the number of gifts.

Use the context. A surname seen with SYED, ASAD, IMRAN is a different population from the same surname
seen with AMIT, NIRAV, PRIYA. Judge the name **as borne by these donors**, not in the abstract.

## Output

One JSON object per input line, in the same order, nothing else (JSON Lines):

{"token": "HADDAD", "origin": "ARABIC", "p_am": 0.97, "conf": "high", "shared": false, "note": "Levantine occupational surname (smith)"}

- `token`: copied exactly.
- `origin`: the single most likely origin code from the list below.
- `p_am`: probability (0 to 1, two decimals) that a donor in this list bearing this name has an
  **Arab-or-Muslim-coded** name as defined below. Calibrate it: of 100 tokens you give 0.80, about 80
  should truly be AM-coded. Do not round toward 0 or 1 when you are unsure.
- `conf`: high / medium / low, your confidence in `origin`.
- `shared`: true when the token is common in an AM tradition **and** a non-AM one
  (SHAH, MALIK, CHAUDHRY, HANNA, SAMUEL, ADAM, SARA, OMAR is not shared, DAVID is not shared).
- `note`: at most 12 words; why. For a transliteration or misspelling, say of what.

## Origin codes

AM-coded (count toward p_am):
- `ARABIC` — Arabic-language name, any religion or country: Levantine (Lebanese, Syrian, Palestinian,
  Jordanian), Iraqi, Gulf, Yemeni, Egyptian, Sudanese, Maghrebi. Includes Arab Christian names
  (HADDAD, KHOURY, NASSAR, HANNA as an Arab surname) and Arabic names used across the Muslim world
  (MOHAMMED, AHMED, FATIMA, ABDULLAH). Includes transliteration variants and ABU/ABD/AL/EL/BIN forms.
- `PERSIAN` — Iranian / Persian / Dari / Tajik names (-ZADEH, -POUR, -NEJAD, TEHRANI, PARVIZ).
- `TURKISH` — Turkish, Azerbaijani and other Turkic names (-OGLU, YILMAZ, ALIYEV).
- `SOUTH_ASIAN_MUSLIM` — Pakistani, Indian Muslim, Bangladeshi Muslim, Kashmiri Muslim names
  (QURESHI, SIDDIQUI, HUSSAIN, CHOUDHURY when seen with Muslim given names).
- `AFGHAN_PASHTO` — Pashtun / Afghan names (POPAL, KARZAI, AFGHAN, -ZAI).
- `SOMALI_EAST_AFRICAN_MUSLIM`, `WEST_AFRICAN_MUSLIM` (Wolof, Fula, Hausa, Mandinka Muslim names),
  `BALKAN_MUSLIM` (Bosniak, Muslim Albanian, e.g. HODZIC, BEGOVIC), `SOUTHEAST_ASIAN_MUSLIM`
  (Malay, Indonesian Muslim), `OTHER_MUSLIM` (Kurdish, Chechen, Uyghur, Central Asian).

Not AM-coded:
- `ASSYRIAN_CHALDEAN` — Aramaic / Syriac-origin Iraqi or Syrian Christian names (YONO, KASSAB only if
  the bearers are clearly Chaldean; SHAMOUN, YALDO, JARJIS). Arabic-language surnames borne by
  Chaldeans stay `ARABIC`; use this code only for Aramaic/Syriac-origin names.
- `ARMENIAN` (-IAN / -YAN, ARMENIAN given names), `JEWISH` (Hebrew, Yiddish, Ashkenazi, Sephardi and
  Mizrahi Jewish names, including Arabic-derived names overwhelmingly borne by Jews such as MIZRAHI,
  SASSON, DWECK), `GREEK`, `MALTESE`.
- `SOUTH_ASIAN_NON_MUSLIM` — Hindu, Sikh, Jain, Indian Christian (PATEL, SINGH, REDDY, IYER).
- `EAST_ASIAN`, `SOUTHEAST_ASIAN_NON_MUSLIM` (Vietnamese, Filipino, Thai), `HISPANIC_LUSOPHONE`.
- `ENGLISH_CELTIC` (English, Scottish, Irish, Welsh), `GERMANIC` (German, Dutch, Nordic, Swiss),
  `ROMANCE` (French, Italian, Romanian), `SLAVIC_BALTIC_HUNGARIAN`, `OTHER_EUROPEAN`.
- `AFRICAN_NON_MUSLIM`, `AFRICAN_AMERICAN` (distinctive African-American given names).
- `BIBLICAL_PAN_CULTURAL` — given names used across Christian, Jewish and Muslim traditions in this
  same spelling (ADAM, SARA, SARAH, JOSEPH, MARIAM, DANIEL, JOHN). p_am should then reflect who in
  this list bears it; the context tells you.
- `OTHER`, `UNKNOWN` — use UNKNOWN when you cannot tell; give p_am your honest base-rate guess.

## Rules

1. Arab Christian, Muslim, Druze and secular bearers of Arabic-language names all count as ARABIC.
   This is a naming convention, not a religion census.
2. A given name such as MOHAMMED counts as AM-coded even if the surname is SMITH.
3. Misspellings and spacing variants count as the name they spell (EZZEDDIN = EZZEDDINE,
   MOHAMAD = MUHAMMAD). Concatenated tokens: ABUATIEH = ABU ATIEH, ELSAYED = EL SAYED.
4. Common English/European surnames that happen to look short or rare are still European
   (BELL, FISH, READ). Do not over-call AM because the list is heavily Arab-American.
5. Never use a person's likely politics, the campaign, or anything except the name and its context.
6. Ties and doubt go in p_am and conf, not in a forced guess.
