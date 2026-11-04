from typing import NamedTuple


class Department(NamedTuple):
    code: str
    name: str


class Region(NamedTuple):
    code: str
    name: str
    departments: tuple[Department, ...]


# INSEE codes.
REGIONS = (
    Region(
        "84",
        "Auvergne-Rhône-Alpes",
        (
            Department("01", "Ain"),
            Department("03", "Allier"),
            Department("07", "Ardèche"),
            Department("15", "Cantal"),
            Department("26", "Drôme"),
            Department("38", "Isère"),
            Department("42", "Loire"),
            Department("43", "Haute-Loire"),
            Department("63", "Puy-de-Dôme"),
            Department("69", "Rhône"),
            Department("73", "Savoie"),
            Department("74", "Haute-Savoie"),
        ),
    ),
    Region(
        "27",
        "Bourgogne-Franche-Comté",
        (
            Department("21", "Côte-d’Or"),
            Department("25", "Doubs"),
            Department("39", "Jura"),
            Department("58", "Nièvre"),
            Department("70", "Haute-Saône"),
            Department("71", "Saône-et-Loire"),
            Department("89", "Yonne"),
            Department("90", "Territoire de Belfort"),
        ),
    ),
    Region(
        "53",
        "Bretagne",
        (
            Department("22", "Côtes-d’Armor"),
            Department("29", "Finistère"),
            Department("35", "Ille-et-Vilaine"),
            Department("56", "Morbihan"),
        ),
    ),
    Region(
        "24",
        "Centre-Val de Loire",
        (
            Department("18", "Cher"),
            Department("28", "Eure-et-Loir"),
            Department("36", "Indre"),
            Department("37", "Indre-et-Loire"),
            Department("41", "Loir-et-Cher"),
            Department("45", "Loiret"),
        ),
    ),
    Region(
        "94",
        "Corse",
        (
            Department("2A", "Corse-du-Sud"),
            Department("2B", "Haute-Corse"),
        ),
    ),
    Region(
        "44",
        "Grand Est",
        (
            Department("08", "Ardennes"),
            Department("10", "Aube"),
            Department("51", "Marne"),
            Department("52", "Haute-Marne"),
            Department("54", "Meurthe-et-Moselle"),
            Department("55", "Meuse"),
            Department("57", "Moselle"),
            Department("67", "Bas-Rhin"),
            Department("68", "Haut-Rhin"),
            Department("88", "Vosges"),
        ),
    ),
    Region(
        "32",
        "Hauts-de-France",
        (
            Department("02", "Aisne"),
            Department("59", "Nord"),
            Department("60", "Oise"),
            Department("62", "Pas-de-Calais"),
            Department("80", "Somme"),
        ),
    ),
    Region(
        "11",
        "Île-de-France",
        (
            Department("75", "Paris"),
            Department("77", "Seine-et-Marne"),
            Department("78", "Yvelines"),
            Department("91", "Essonne"),
            Department("92", "Hauts-de-Seine"),
            Department("93", "Seine-Saint-Denis"),
            Department("94", "Val-de-Marne"),
            Department("95", "Val-d’Oise"),
        ),
    ),
    Region(
        "28",
        "Normandie",
        (
            Department("14", "Calvados"),
            Department("27", "Eure"),
            Department("50", "Manche"),
            Department("61", "Orne"),
            Department("76", "Seine-Maritime"),
        ),
    ),
    Region(
        "75",
        "Nouvelle-Aquitaine",
        (
            Department("16", "Charente"),
            Department("17", "Charente-Maritime"),
            Department("19", "Corrèze"),
            Department("23", "Creuse"),
            Department("24", "Dordogne"),
            Department("33", "Gironde"),
            Department("40", "Landes"),
            Department("47", "Lot-et-Garonne"),
            Department("64", "Pyrénées-Atlantiques"),
            Department("79", "Deux-Sèvres"),
            Department("86", "Vienne"),
            Department("87", "Haute-Vienne"),
        ),
    ),
    Region(
        "76",
        "Occitanie",
        (
            Department("09", "Ariège"),
            Department("11", "Aude"),
            Department("12", "Aveyron"),
            Department("30", "Gard"),
            Department("31", "Haute-Garonne"),
            Department("32", "Gers"),
            Department("34", "Hérault"),
            Department("46", "Lot"),
            Department("48", "Lozère"),
            Department("65", "Hautes-Pyrénées"),
            Department("66", "Pyrénées-Orientales"),
            Department("81", "Tarn"),
            Department("82", "Tarn-et-Garonne"),
        ),
    ),
    Region(
        "52",
        "Pays de la Loire",
        (
            Department("44", "Loire-Atlantique"),
            Department("49", "Maine-et-Loire"),
            Department("53", "Mayenne"),
            Department("72", "Sarthe"),
            Department("85", "Vendée"),
        ),
    ),
    Region(
        "93",
        "Provence-Alpes-Côte d’Azur",
        (
            Department("04", "Alpes-de-Haute-Provence"),
            Department("05", "Hautes-Alpes"),
            Department("06", "Alpes-Maritimes"),
            Department("13", "Bouches-du-Rhône"),
            Department("83", "Var"),
            Department("84", "Vaucluse"),
        ),
    ),
    Region("01", "Guadeloupe", (Department("971", "Guadeloupe"),)),
    Region("02", "Martinique", (Department("972", "Martinique"),)),
    Region("03", "Guyane", (Department("973", "Guyane"),)),
    Region("04", "La Réunion", (Department("974", "La Réunion"),)),
    Region("06", "Mayotte", (Department("976", "Mayotte"),)),
    Region("99", "Pays étranger", (Department("99", "Pays étranger"),)),
)

DEPARTMENT_CODES = {department.code for region in REGIONS for department in region.departments}

# Corsica's postal codes all start with 20 rather than with their department's code.
CORSICA_POSTAL_CODES = {"2A": r"^20[01]", "2B": r"^20[2-6]"}
