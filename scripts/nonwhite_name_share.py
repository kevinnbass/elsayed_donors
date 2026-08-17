"""Share of named-itemized $ from non-Anglo / non-White-coded American names.

Name tokens only. Not a race census. Muslim-coded names are a subset.
"""
from __future__ import annotations

import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "muslim_name_share", ROOT / "scripts" / "muslim_name_share.py"
)
mus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mus)

# Hispanic / Latino surnames (common US).
HISPANIC_LAST = {
    "GARCIA", "RODRIGUEZ", "MARTINEZ", "HERNANDEZ", "LOPEZ", "GONZALEZ",
    "PEREZ", "SANCHEZ", "RAMIREZ", "TORRES", "FLORES", "RIVERA", "GOMEZ",
    "DIAZ", "REYES", "MORALES", "CRUZ", "ORTIZ", "GUTIERREZ", "CHAVEZ",
    "RAMOS", "MENDOZA", "RUIZ", "ALVAREZ", "JIMENEZ", "CASTILLO", "VASQUEZ",
    "ROMERO", "HERRERA", "MEDINA", "AGUILAR", "VARGAS", "GUZMAN", "MENDEZ",
    "MUNOZ", "SALAZAR", "SOTO", "DELGADO", "PENA", "RIOS", "ALVARADO",
    "SANDOVAL", "CONTRERAS", "GUERRERO", "ESTRADA", "LUNA", "ESPINOZA",
    "DOMINGUEZ", "JUAREZ", "VEGA", "SILVA", "PADILLA", "CERVANTES",
    "CABRERA", "NUNEZ", "ORTEGA", "SANTIAGO", "MORENO", "ROJAS",
    "CORTES", "FIGUEROA", "ACOSTA", "MARQUEZ", "LEON", "CAMPO",
    "RODRIQUEZ", "GARZA", "FERNANDEZ", "VALDEZ", "MALDONADO", "SANTOS",
    "COLON", "VALENCIA", "VELASQUEZ", "VELAZQUEZ", "DEJESUS", "DELACRUZ",
    "CARDENAS", "FUENTES", "SALAS", "CALDERON", "VALENZUELA", "ACEVEDO",
    "BARRERA", "ROSALES", "CASTANEDA", "MACIAS", "SOSA", "NIEVES",
    "ROCHA", "CANTU", "MELENDEZ", "AGUIRRE", "FRANCO", "OCHOA",
    "ROSARIO", "SANTANA", "SUAREZ", "MEJIA", "RIVAS", "SOLIS",
    "TRUJILLO", "VILLARREAL", "CARRILLO", "LARA", "MERCADO", "VELEZ",
    "CAMACHO", "DURAN", "NAVARRO", "ROBLES", "AVILA", "TREVINO",
    "SALINAS", "CAMPOS", "MONTOYA", "GALLEGOS", "MIRANDA", "PACHECO",
    "SERRANO", "AYALA", "VAZQUEZ", "MOLINA", "DELEON",
}

# Levantine / MENA names often Christian or mixed (not counted as Muslim).
LEVANTINE_LAST = {
    "HADDAD", "KHOURY", "KHOURI", "ABDO", "ABDOU", "CHAMI", "DUDUM",
    "FREIJ", "SHEHADI", "AZAR", "BATTAT", "MUALLEM", "HABAYEB",
    "FAKHOURY", "FAKHORY", "BASHA", "HARAJLI", "ALO", "DAOUD",
    "SHAHBANDAR", "MIZRAHY", "MIZRAHI", "SIAM", "SALEM",
    "ANDONI", "HOMSI", "SHAMI", "TARAZI", "HOURANI", "NASSAR",
    "SABAGH", "DAYE", "BISHARAT", "SAROFIM", "SINNO", "SARAFA",
}

# East / Southeast Asian surnames. LEE/PARK/KIM kept (mostly Korean/Chinese in this file).
EAST_ASIAN_LAST = {
    "CHEN", "WANG", "LI", "ZHANG", "LIU", "YANG", "HUANG", "WU", "ZHOU",
    "XU", "SUN", "MA", "ZHU", "HU", "GUO", "HE", "LIN", "GAO", "LUO",
    "ZHENG", "LIANG", "XIE", "TANG", "SONG", "DENG", "HAN", "CAO", "FENG",
    "PENG", "XIAO", "KIM", "PARK", "CHOI", "JUNG", "CHO", "KANG", "YOON",
    "LEE",  # ambiguous; counted non-Anglo here
    "NGUYEN", "TRAN", "LE", "PHAM", "HOANG", "PHAN", "VU", "VO", "DANG",
    "BUI", "DO", "HO", "NGO", "DUONG", "LY",
    "TANAKA", "SUZUKI", "SATO", "WATANABE", "TAKAHASHI",
    "LU", "CHULAMORKODT", "WONG", "CHANG", "CHAN", "CHENG",
    "CHOW", "LAU", "LAM", "HO", "NG", "TANG", "TSANG",
    "YEE", "YIP", "CHEUNG", "LEUNG", "KWOK", "LAI",
    "NGHOEM",
}

SOUTH_ASIAN_LAST = {
    "PATEL", "SINGH", "SHARMA", "SHETTY", "REDDY", "RAO", "NAIR", "IYER",
    "KRISHNAN", "KRISHNA", "GUPTA", "MEHTA", "JOSHI", "DESAI", "SHAH",
    "KAPOOR", "CHOPRA", "MALHOTRA", "BANERJEE", "MUKHERJEE", "CHATTERJEE",
    "DAS", "BOSE", "SEN", "GHOSH", "ROY", "DUTTA",
    "PILLAI", "MENON", "NAIR", "KUMAR", "VERMA", "AGARWAL", "AGRAWAL",
    "JAIN", "BANSAL", "SAXENA", "MISHRA", "TIWARI", "PANDEY", "YADAV",
    "THAKUR", "CHAUHAN", "RATHORE",
    "PERERA", "FERNANDO", "JAYAWARDENA",
    "NATHOO", "GODIL", "AFZAL", "SUMAR", "MOLLA", "SIDEEKA",
    "CHAKRABARTI", "CHAKRABARTY", "VASAN", "LAL", "KHATRI",
    "CHOKHANI", "BAWA", "MALWATTE", "MAKHIAWALA", "SOPHIE",
    "PERERA", "JAYAWARDENA", "BANDARA", "DISSANAYAKE",
    "IYENGAR", "SRINIVASAN", "VENKATESH", "VENKAT",
    "SUBRAMANIAN", "RAMACHANDRAN", "NARAYAN", "NARAYANAN",
    "BALAKRISHNAN", "RAJAGOPAL", "PRASAD", "CHANDRA",
    "BANERJI", "MUKHERJI", "BHATTACHARYA", "BHATTACHARYYA",
    "GANGULY", "DATTA", "NAIDU", "HEGDE", "KULKARNI", "PATIL",
    "JADHAV", "PALAVALI", "UBHI", "RUNGTA", "YALAMANCHI",
    "MOHAN",
}

# Distinctive African / African-American given names (high precision, low recall).
AFRICAN_FIRST = {
    "JAMAL", "LAKEISHA", "LAKEISHA", "DEANDRE", "DEANDRE", "KEISHA",
    "LATASHA", "MARQUIS", "MARQUISE", "TYRONE", "SHANICE", "ASHANTI",
    "IME", "KWAME", "KOFI", "AMA", "ADWOA", "CHINEDU", "CHUKWU", "OBI",
    "NIA", "ZURI", "IMANI",
}

# Clearly Anglo / Western European surnames (not exhaustive; used to label WHITE).
ANGLO_LAST = {
    "SMITH", "JOHNSON", "WILLIAMS", "BROWN", "JONES", "MILLER", "DAVIS",
    "WILSON", "MOORE", "TAYLOR", "ANDERSON", "THOMAS", "JACKSON", "WHITE",
    "HARRIS", "MARTIN", "THOMPSON", "ROBINSON", "CLARK", "LEWIS", "WALKER",
    "HALL", "ALLEN", "YOUNG", "KING", "WRIGHT", "SCOTT", "GREEN", "BAKER",
    "ADAMS", "NELSON", "HILL", "RAMSEY", "CAMPBELL", "MITCHELL", "ROBERTS",
    "CARTER", "PHILLIPS", "EVANS", "TURNER", "TORRES", "PARKER", "COLLINS",
    "EDWARDS", "STEWART", "MORRIS", "MURPHY", "COOK", "ROGERS", "MORGAN",
    "COOPER", "RICHARDSON", "COX", "HOWARD", "WARD", "TORRES", "PETERSON",
    "GRAY", "RAMIREZ", "JAMES", "WATSON", "BROOKS", "KELLY", "SANDERS",
    "PRICE", "BENNETT", "WOOD", "BARNES", "ROSS", "HENDERSON", "COLEMAN",
    "JENKINS", "PERRY", "POWELL", "LONG", "PATTERSON", "HUGHES", "FLORES",
    "WASHINGTON", "BUTLER", "SIMMONS", "FOSTER", "GONZALES", "BRYANT",
    "ALEXANDER", "RUSSELL", "GRIFFIN", "DIAZ", "HAYES", "MYERS", "FORD",
    "HAMILTON", "GRAHAM", "SULLIVAN", "WALLACE", "WOODS", "COLE", "WEST",
    "JORDAN", "OWENS", "REYNOLDS", "FISHER", "ELLIS", "HARRISON", "GIBSON",
    "MCDONALD", "CRUZ", "MARSHALL", "ORTIZ", "GOMEZ", "MURRAY", "FREEMAN",
    "WELLS", "WEBB", "SIMPSON", "STEVENS", "TUCKER", "PORTER", "HUNTER",
    "HICKS", "CRAWFORD", "HENRY", "BOYD", "MASON", "MORALES", "KENNEDY",
    "WARREN", "DIXON", "RAMOS", "REYES", "BURNS", "GORDON", "SHAW",
    "HOLMES", "RICE", "ROBERTSON", "HUNT", "BLACK", "DANIELS", "PALMER",
    "MILLS", "NICHOLS", "GRANT", "KNIGHT", "FERGUSON", "ROSE", "STONE",
    "HAWKINS", "DUNN", "PERKINS", "HUDSON", "SPENCER", "GARDNER", "STEPHENS",
    "PAYNE", "PIERCE", "BERRY", "MATTHEWS", "ARNOLD", "WAGNER", "WILLIS",
    "RAY", "WATKINS", "OLSON", "CARROLL", "DUNCAN", "SNYDER", "HART",
    "CUNNINGHAM", "BRADLEY", "LANE", "ANDREWS", "RUIZ", "HARPER", "FOX",
    "RILEY", "ARMSTRONG", "CARPENTER", "WEAVER", "GREENE", "LAWRENCE",
    "ELLIOTT", "CHAVEZ", "SIMS", "AUSTIN", "PETERS", "KELLEY", "FRANKLIN",
    "LAWSON", "FIELDS", "GUTIERREZ", "RYAN", "SCHMIDT", "CARR", "VASQUEZ",
    "CASTILLO", "WHEELER", "CHAPMAN", "OLIVER", "MONTGOMERY", "RICHARDS",
    "WILLIAMSON", "JOHNSTON", "BANKS", "MEYER", "BISHOP", "MCCOY", "HOWELL",
    "ALVAREZ", "MORRISON", "HANSEN", "FERNANDEZ", "GARZA", "HARVEY",
    "LITTLE", "BURTON", "STANLEY", "NGUYEN", "GEORGE", "JACOBS", "REID",
    "KIM", "FULLER", "LYNCH", "DEAN", "GILBERT", "GARRETT", "ROMERO",
    "WELCH", "LARSON", "FRAZIER", "BURKE", "HANSON", "DAY", "MENDOZA",
    "MORENO", "BOWMAN", "MEDINA", "FOWLER", "BREWER", "HOFFMAN", "CARLSON",
    "SILVA", "PEARSON", "HOLLAND", "DOUGLAS", "FLEMING", "JENSEN", "VARGAS",
    "BYRD", "DAVIDSON", "HOPKINS", "MAY", "TERRY", "HERRERA", "WADE",
    "SOTO", "WALTERS", "CURTIS", "NEAL", "CALDWELL", "LOWE", "JENNINGS",
    "BARNETT", "GRAVES", "JIMENEZ", "HORTON", "SHELTON", "BARRETT", "OBRIEN",
    "CASTRO", "SUTTON", "GREGORY", "MCKINNEY", "LUCAS", "MILES", "CRAIG",
    "RODRIQUEZ", "CHAMBERS", "HOLT", "LAMBERT", "FLETCHER", "WATTS", "BATES",
    "HALE", "RHODES", "PENA", "BECK", "NEWMAN", "HAYNES", "MCDANIEL",
    "MENDEZ", "BUSH", "VAUGHN", "PARKS", "DAWSON", "SANTIAGO", "NORRIS",
    "HARDY", "LOVE", "STEELE", "CURRY", "POWERS", "SCHULTZ", "BARKER",
    "GUZMAN", "PAGE", "MUNOZ", "BALL", "KELLER", "CHANDLER", "WEBER",
    "LEONARD", "WALSH", "LYONS", "RAMSEY", "WOLFE", "SCHNEIDER", "MULLINS",
    "BENSON", "SHARP", "BOWEN", "DANIEL", "BARBER", "CUMMINGS", "HINES",
    "BALDWIN", "GRIFFITH", "VALDEZ", "HUBBARD", "SALAZAR", "REEVES",
    "WARNER", "STEVENSON", "BURGESS", "SANTOS", "TATE", "CROSS", "GARNER",
    "MANN", "MACK", "MOSS", "THORNTON", "DENNIS", "MCGEE", "FARMER",
    "DELGADO", "AGUILAR", "VEGA", "GLOVER", "MANNING", "COHEN", "HARMON",
    "RODGERS", "ROBBINS", "NEWTON", "TODD", "BLAIR", "HIGGINS", "INGRAM",
    "REESE", "CANNON", "STRICKLAND", "TOWNSEND", "POTTER", "GOODWIN",
    "WALTON", "ROWE", "HAMPTON", "ORTEGA", "PATTON", "SWANSON", "JOSEPH",
    "FRANCIS", "GOODMAN", "MALDONADO", "YATES", "BECKER", "ERICKSON",
    "HODGES", "RIOS", "CONNER", "ADKINS", "WEBSTER", "NORMAN", "MALONE",
    "HAMMOND", "FLOWERS", "COBB", "MOODY", "QUINN", "BLAKE", "MAXWELL",
    "POPE", "FLOYD", "OSBORNE", "PAUL", "MCCARTHY", "GUERRERO", "LINDSEY",
    "ESTRADA", "SANDOVAL", "GIBBS", "TYLER", "GROSS", "FITZGERALD", "STOKES",
    "DOYLE", "SHERMAN", "SAUNDERS", "WISE", "COLON", "GILL", "ALVARADO",
    "GREER", "PADILLA", "SIMON", "WATERS", "NUNEZ", "BALLARD", "SCHWARTZ",
    "MCBRIDE", "HOUSTON", "CHRISTENSEN", "KLEIN", "PRATT", "BRIGGS",
    "PARSONS", "MCLAUGHLIN", "ZIMMERMAN", "FRENCH", "BUCHANAN", "MORAN",
    "COPELAND", "ROY", "PITTMAN", "BRADY", "MCCORMICK", "HOLLOWAY", "BROCK",
    "POOLE", "FRANK", "LOGAN", "OWEN", "BASS", "MARSH", "DRAKE", "WONG",
    "JEFFERSON", "PARK", "MORTON", "ABBOTT", "SPARKS", "PATRICK", "NORTON",
    "HUFF", "CLAYTON", "MASSEY", "LLOYD", "FIGUEROA", "CARSON", "BOWERS",
    "ROBERSON", "BARTON", "TRAN", "LAMB", "HARRINGTON", "CASEY", "BOONE",
    "CORTEZ", "CLARKE", "MATHIS", "SINGLETON", "WILKINS", "CAIN", "BRYAN",
    "UNDERWOOD", "HOGAN", "MCKENZIE", "COLLIER", "LUNA", "PHELPS", "MCGUIRE",
    "ALLISON", "BRIDGES", "WILKERSON", "NASH", "SUMMERS", "ATKINS", "WILCOX",
    "PITTS", "CONLEY", "MARQUEZ", "BURNETT", "RICHARD", "COCHRAN", "CHASE",
    "DAVENPORT", "HOOD", "GATES", "CLAY", "AYALA", "SAWYER", "ROMAN", "VAZQUEZ",
    "DICKERSON", "HODGE", "ACOSTA", "FLYNN", "ESPINOZA", "NICHOLSON", "MONROE",
    "WOLF", "MORROW", "KIRK", "RANDALL", "ANTHONY", "WHITAKER", "OCONNOR",
    "SKINNER", "WARE", "MOLINA", "KIRBY", "HUFFMAN", "BRADFORD", "CHARLES",
    "GILMORE", "DOMINGUEZ", "ONEAL", "BRUCE", "LANG", "COMBS", "KRAMER",
    "HEATH", "HANCOCK", "GALLAGHER", "GAINES", "SHAFFER", "SHORT", "WIGGINS",
    "MATHEWS", "MCCLAIN", "FISCHER", "WALL", "SMALL", "MELTON", "HENSLEY",
    "BOND", "DYER", "CAMERON", "GRIMES", "CONTRERAS", "CHRISTIAN", "WYATT",
    "BAXTER", "SNOW", "MOSLEY", "SHEPHERD", "LARSEN", "HOOVER", "BEASLEY",
    "GLENN", "PETERSEN", "WHITEHEAD", "MEYERS", "KEITH", "GARRISON", "VINCENT",
    "SHIELDS", "HORN", "SAVAGE", "OLSEN", "SCHROEDER", "HARTMAN", "WOODARD",
    "MUELLER", "KEMP", "DELEON", "BOOTH", "PATEL", "CALHOUN", "WILEY", "EATON",
    "CLINE", "NAVARRO", "HARRELL", "LESTER", "HUMPHREY", "PARRISH", "DURAN",
    "HUTCHINSON", "HESS", "DORSEY", "BULLOCK", "ROBLES", "BEARD", "DALTON",
    "AVILA", "VANCE", "RICH", "BLACKWELL", "YORK", "JOHNS", "BLANKENSHIP",
    "TREVINO", "SALINAS", "CAMPOS", "PRUITT", "MOSES", "CALLAHAN", "GOLDEN",
    "MONTOYA", "HARDIN", "GUERRA", "MCDOWELL", "CAREY", "STAFFORD", "GALLEGOS",
    "HENSON", "WILKINSON", "BOOKER", "MERRITT", "MIRANDA", "ATKINSON", "ORR",
    "DECKER", "HOBBS", "PRESTON", "TANNER", "KNOX", "PACHECO", "STEPHENSON",
    "GLASS", "ROJAS", "SERRANO", "MARKS", "HICKMAN", "ENGLISH", "SWEENEY",
    "STRONG", "PRINCE", "MCCLURE", "CONWAY", "WALTER", "ROTH", "MAYNARD",
    "FARRELL", "LOWERY", "HURST", "NIXON", "WEISS", "TRUJILLO", "ELLISON",
    "SLOAN", "JUAREZ", "WINTERS", "MCLEAN", "RANDOLPH", "LEON", "BOYER",
    "VILLARREAL", "MCCALL", "GENTRY", "CARRILLO", "KENT", "AYERS", "LARA",
    "SHANNON", "SEXTON", "PACE", "HULL", "LEBLANC", "BROWNING", "VELASQUEZ",
    "LEACH", "CHANG", "HOUSE", "SELLERS", "HERRING", "NOBLE", "FOLEY",
    "BARTLETT", "MERCADO", "LANDRY", "DURHAM", "WALLS", "BARR", "MCKEE",
    "BAUER", "RIVERS", "EVERETT", "BRADSHAW", "PUGH", "VELEZ", "RUSH",
    "ESTES", "DODSON", "MORSE", "SHEPPARD", "WEEKS", "CAMACHO", "BEAN",
    "BARRON", "LIVINGSTON", "MIDDLETON", "SPEARS", "BRANCH", "BLEVINS",
    "CHEN", "KERR", "MCCONNELL", "HATFIELD", "HARDING", "ASHLEY", "SOLIS",
    "HERMAN", "FROST", "GILES", "BLACKBURN", "WILLIAM", "PENNINGTON",
    "WOODWARD", "FINLEY", "MCINTOSH", "KOCH", "BEST", "SOLOMON", "MCCULLOUGH",
    "DUDLEY", "NOLAN", "BLANCHARD", "RIVAS", "BRENNAN", "MEJIA", "KANE",
    "BENTON", "JOYCE", "BUCKLEY", "HALEY", "VALENTINE", "MADDOX", "RUSSO",
    "MCKNIGHT", "BUCK", "MOON", "MCMILLAN", "CROSBY", "BERG", "DOTSON",
    "MAYS", "ROACH", "CHURCH", "CHAN", "RICHMOND", "MEADOWS", "FAULKNER",
    "ONEILL", "KNAPP", "KLINE", "BARRY", "OCHOA", "JACOBSON", "GAY", "AVERY",
    "HENDRICKS", "HORNE", "SHEPARD", "HEBERT", "CHERRY", "CARDENAS", "MCINTYRE",
    "WHITNEY", "WALLER", "HOLMAN", "DONALDSON", "CANTU", "TERRELL", "MORIN",
    "GILLESPIE", "FUENTES", "TILLMAN", "SANFORD", "BENTLEY", "PECK", "KEY",
    "SALAS", "ROLLINS", "GAMBLE", "DICKSON", "BATTLE", "SANTANA", "CABRERA",
    "CERVANTES", "HOWE", "HINTON", "HURLEY", "SPENCE", "ZAMORA", "YANG",
    "MCNEIL", "SUAREZ", "CASE", "PETTY", "GOULD", "MCFARLAND", "SAMPSON",
    "CARVER", "BRAY", "ROSARIO", "MACDONALD", "STOUT", "HESTER", "MELENDEZ",
    "DILLON", "FARLEY", "HOPPER", "GALLOWAY", "POTTS", "BERNARD", "JOYNER",
    "STEIN", "AGUIRRE", "OSBORN", "MERCER", "BENDER", "FRANCO", "ROWLAND",
    "SYKES", "BENJAMIN", "TRAVIS", "PICKETT", "CRANE", "SEARS", "MAYO",
    "DUNLAP", "HAYDEN", "WILDER", "MCKAY", "COFFEY", "MCCARTY", "EWING",
    "COOLEY", "VAUGHAN", "BONNER", "COTTON", "HOLDER", "STARK", "FERRELL",
    "CANTRELL", "FULTON", "LYNN", "LOTT", "CALDERON", "ROSA", "POLLARD",
    "HOOPER", "BURCH", "MULLEN", "FRY", "RIDDLE", "LEVY", "DAVID", "DUKE",
    "ODONNELL", "GUY", "MICHAEL", "BRITT", "FREDERICK", "DAUGHERTY", "BERGER",
    "DILLARD", "ALSTON", "JARVIS", "FRYE", "RIGGS", "CHANEY", "ODOM", "DUFFY",
    "FITZPATRICK", "VALENZUELA", "MERRILL", "MAYER", "ALFORD", "MCPHERSON",
    "ACEVEDO", "DONOVAN", "BARRERA", "ALBERT", "COTE", "REILLY", "COMPTON",
    "RAYMOND", "MOONEY", "MCGOWAN", "CRAFT", "CLEVELAND", "CLEMONS", "WYNN",
    "NIELSEN", "BAIRD", "STANTON", "SNIDER", "ROSALES", "BRIGHT", "WITT",
    "STUART", "HAYS", "HOLDEN", "RUTLEDGE", "KINNEY", "CLEMENTS", "CASTANEDA",
    "SLATER", "HAHN", "EMERSON", "CONRAD", "BURKS", "DELANEY", "PATE",
    "LANCASTER", "SWEET", "JUSTICE", "TYSON", "SHARPE", "WHITFIELD", "TALLEY",
    "MACIAS", "IRWIN", "BURRIS", "RATLIFF", "MCCRAY", "MADDEN", "KAUFMAN",
    "BEACH", "GOFF", "CASH", "BOLTON", "MCFADDEN", "LEVINE", "GOOD", "BYERS",
    "KIRKLAND", "KIDD", "WORKMAN", "CARNEY", "DALE", "MCLEOD", "HOLCOMB",
    "ENGLAND", "FINCH", "HEAD", "BURT", "HENDRIX", "SOSA", "HANEY", "FRANKS",
    "SARGENT", "NIEVES", "DOWNS", "RASMUSSEN", "BIRD", "HEWITT", "LINDSAY",
    "LE", "FOREMAN", "VALENCIA", "ONEIL", "DELACRUZ", "VINSON", "DEJESUS",
    "HYDE", "FORBES", "GILLIAM", "GUTHRIE", "WOOTEN", "HUBER", "BARLOW",
    "BOYLE", "MCMAHON", "BUCKNER", "ROCHA", "PUCKETT", "LANGLEY", "KNOWLES",
    "COOKE", "VELAZQUEZ", "WHITLEY", "NOEL", "VANG",
    # high-dollar Anglo names seen in this roster
    "CLIFFORD", "SKLOFF", "KOKORIS", "VANBELLE", "JURVETSON", "AUERBACH",
    "CONNELL", "PENNINGTON", "LANGHORNE", "SAGINAW",
    "HARTLE", "FAVREAU", "PRITZKER", "RAGLAND", "POLLICELLA",
    "WACHTEL", "SHEFTS", "CUKIER", "SCANLON", "VLOCK",
    "HILGART", "KAMP", "STOLLER", "HORNSTEIN", "MCLEES",
    "GLEICHER", "KRUSE", "SPRIGGS", "HAGGERTY", "KEENER",
    "LEIKE", "MAVRIDES",
    "WOOLVERTON", "ZIEGLER", "SANDERLIN", "CLONEY", "GENSLER",
    "LATHAM", "GOLDMAN", "ROOT", "HAAS", "DONNELLY", "BRICKELL",
    "COOLIDGE", "KRAHN", "PERETHS", "BLAUVELT", "MURPHEY",
    "STEIGERWALT", "GOLD", "MEISTER", "NORR", "SPURR",
    "BASSETT", "MCCORMACK", "ROULEAU", "LIGHTY", "SEEGER",
    "VANZIELEGHEM", "BOAL", "KAHN",
}

WESTERN_FIRST = {
    "JAMES", "JOHN", "ROBERT", "MICHAEL", "WILLIAM", "DAVID", "RICHARD",
    "JOSEPH", "THOMAS", "CHARLES", "CHRISTOPHER", "DANIEL", "MATTHEW",
    "ANTHONY", "MARK", "DONALD", "STEVEN", "PAUL", "ANDREW", "JOSHUA",
    "KENNETH", "KEVIN", "BRIAN", "GEORGE", "TIMOTHY", "RONALD", "EDWARD",
    "JASON", "JEFFREY", "RYAN", "JACOB", "GARY", "NICHOLAS", "ERIC",
    "JONATHAN", "STEPHEN", "LARRY", "JUSTIN", "SCOTT", "BRANDON", "BENJAMIN",
    "SAMUEL", "GREGORY", "FRANK", "ALEXANDER", "RAYMOND", "PATRICK", "JACK",
    "DENNIS", "JERRY", "TYLER", "AARON", "JOSE", "ADAM", "HENRY", "NATHAN",
    "DOUGLAS", "ZACHARY", "PETER", "KYLE", "WALTER", "ETHAN", "JEREMY",
    "HAROLD", "KEITH", "CHRISTIAN", "ROGER", "NOAH", "GERALD", "CARL",
    "TERRY", "SEAN", "AUSTIN", "ARTHUR", "LAWRENCE", "JESSE", "DYLAN",
    "BRYAN", "JOE", "JORDAN", "BILLY", "BRUCE", "ALBERT", "WILLIE",
    "GABRIEL", "LOGAN", "ALAN", "JUAN", "WAYNE", "ROY", "RALPH", "RANDY",
    "EUGENE", "VINCENT", "RUSSELL", "LOUIS", "PHILIP", "BOBBY", "JOHNNY",
    "BRADLEY",
    "MARY", "PATRICIA", "JENNIFER", "LINDA", "ELIZABETH", "BARBARA",
    "SUSAN", "JESSICA", "SARAH", "KAREN", "NANCY", "LISA", "BETTY",
    "MARGARET", "SANDRA", "ASHLEY", "KIMBERLY", "EMILY", "DONNA", "MICHELLE",
    "DOROTHY", "CAROL", "AMANDA", "MELISSA", "DEBORAH", "STEPHANIE",
    "REBECCA", "SHARON", "LAURA", "CYNTHIA", "KATHLEEN", "AMY", "ANGELA",
    "SHIRLEY", "ANNA", "BRENDA", "PAMELA", "EMMA", "NICOLE", "HELEN",
    "SAMANTHA", "KATHERINE", "CHRISTINE", "DEBRA", "RACHEL", "CAROLYN",
    "JANET", "CATHERINE", "MARIA", "HEATHER", "DIANE", "RUTH", "JULIE",
    "OLIVIA", "JOYCE", "VIRGINIA", "VICTORIA", "KELLY", "LAUREN",
    "CHRISTINA", "JOAN", "EVELYN", "JUDITH", "ANDREA", "HANNAH", "MEGAN",
    "CHERYL", "JACQUELINE", "MARTHA", "GLORIA", "TERESA", "ANN", "SARA",
    "MADISON", "FRANCES", "KATHRYN", "JANICE", "JEAN", "ABIGAIL", "ALICE",
    "JUDY", "SOPHIA", "GRACE", "DENISE", "AMBER", "DORIS", "MARILYN",
    "DANIELLE", "BEVERLY", "ISABELLA", "THERESA", "DIANA", "NATALIE",
    "BRITTANY", "CHARLOTTE", "MARIE", "KAYLA", "ALEXIS", "LORI",
    "ANDY", "STEVE", "LYNDSEY", "KARLA", "KENNETH", "PAUL", "LORI",
    "MICHAEL", "JAMES", "WILLIAM", "DAVID", "BRANDON",
}


def last_first(name: str) -> tuple[str, str]:
    last, first = mus.tokens(name)
    return last.replace(" ", ""), first


def bucket(name: str) -> str:
    last, first = last_first(name)
    if not last and not first:
        return "unknown"
    mcls = mus.classify(name)
    if mcls != "no":
        return "arab_or_muslim"
    last_parts = set(last.replace("-", " ").split()) | {last}
    if last in LEVANTINE_LAST or last_parts & LEVANTINE_LAST:
        return "levantine_mena"
    if last in HISPANIC_LAST or last_parts & HISPANIC_LAST:
        return "hispanic_latino"
    if last in SOUTH_ASIAN_LAST or last_parts & SOUTH_ASIAN_LAST:
        return "south_asian"
    if last in EAST_ASIAN_LAST or last_parts & EAST_ASIAN_LAST:
        return "east_asian"
    if first in AFRICAN_FIRST:
        return "african_distinctive"
    # Levantine/Arab Christian leftovers already in HISPANIC_LAST as non-Anglo
    if last in ANGLO_LAST or (last_parts & ANGLO_LAST):
        return "anglo_white"
    if first in WESTERN_FIRST and last not in mus.LAST:
        # Western first + unknown last: still ambiguous unless last looks Anglo-ish
        if re.fullmatch(r"[A-Z]{3,12}", last) and last.endswith(("SON", "SEN", "BERG", "STEIN", "FORD", "TON", "LEY", "WELL", "WOOD", "FIELD", "MAN")):
            return "anglo_white"
        return "ambiguous"
    return "ambiguous"


def main() -> None:
    gift = defaultdict(lambda: {"n": 0, "amt": 0.0})
    donors = defaultdict(lambda: {"amt": 0.0, "n": 0, "name": "", "bucket": ""})
    tot = 0.0
    roster = ROOT / "analysis" / "roster_named_itemized.jsonl"
    with roster.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            tot += r["amt"]
            b = bucket(r.get("name") or "")
            gift[b]["n"] += 1
            gift[b]["amt"] += r["amt"]
            k = (r.get("last_norm"), r.get("first_norm"))
            d = donors[k]
            d["amt"] += r["amt"]
            d["n"] += 1
            d["name"] = r.get("name") or ""
            d["bucket"] = b

    nonwhite = (
        gift["arab_or_muslim"]["amt"]
        + gift["levantine_mena"]["amt"]
        + gift["hispanic_latino"]["amt"]
        + gift["south_asian"]["amt"]
        + gift["east_asian"]["amt"]
        + gift["african_distinctive"]["amt"]
    )
    # broader: everything except anglo_white (ambiguous counted as non-Anglo)
    non_anglo_incl_ambig = tot - gift["anglo_white"]["amt"] - gift["unknown"]["amt"]
    out = {
        "named_itemized_total": round(tot, 2),
        "method": (
            "Name-token classifier. Non-white-coded = Arab-or-Muslim "
            "(includes Levantine Christian surnames) OR leftover Levantine "
            "OR Hispanic/Latino OR South Asian OR East/Southeast Asian "
            "OR a small African-American given-name list. Anglo/White-coded "
            "= common US/European/Ashkenazi surnames. Not a race census."
        ),
        "nonwhite_coded": {
            "amt": round(nonwhite, 2),
            "pct": round(100.0 * nonwhite / tot, 1),
        },
        "non_anglo_including_ambiguous": {
            "amt": round(non_anglo_incl_ambig, 2),
            "pct": round(100.0 * non_anglo_incl_ambig / tot, 1),
            "note": "Everything except clearly Anglo/White surnames.",
        },
        "anglo_white_coded": {
            "amt": round(gift["anglo_white"]["amt"], 2),
            "pct": round(100.0 * gift["anglo_white"]["amt"] / tot, 1),
        },
        "by_bucket": {
            k: {
                "amt": round(v["amt"], 2),
                "n_gifts": v["n"],
                "pct": round(100.0 * v["amt"] / tot, 1),
            }
            for k, v in sorted(gift.items(), key=lambda kv: -kv[1]["amt"])
        },
        "top15_nonwhite": [
            {"name": d["name"], "amt": round(d["amt"], 2), "bucket": d["bucket"]}
            for d in sorted(
                (x for x in donors.values() if x["bucket"] not in {"anglo_white", "ambiguous", "unknown"}),
                key=lambda x: -x["amt"],
            )[:15]
        ],
        "top15_anglo": [
            {"name": d["name"], "amt": round(d["amt"], 2), "bucket": d["bucket"]}
            for d in sorted(
                (x for x in donors.values() if x["bucket"] == "anglo_white"),
                key=lambda x: -x["amt"],
            )[:15]
        ],
    }
    dest = ROOT / "analysis" / "nonwhite_name_share.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if not k.startswith("top")}, indent=2))
    print("\nTop nonwhite")
    for r in out["top15_nonwhite"]:
        print(f"  {r['name']} — ${r['amt']:,.0f} — {r['bucket']}")
    print("\nTop Anglo-coded")
    for r in out["top15_anglo"]:
        print(f"  {r['name']} — ${r['amt']:,.0f}")
    print("WROTE", dest)


if __name__ == "__main__":
    main()
