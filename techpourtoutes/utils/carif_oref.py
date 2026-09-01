import re

from techpourtoutes.models.level import Level

LEADING_NUMBER = re.compile(r"^(?P<number>\d)\b")

# Cadre national des certifications professionnelles, as the catalogue spells it out:
# "5 (BTS, DEUST...)". Only 3 to 7 ever appear in the published perimeter.
EXIT_LEVELS = {
    "3": Level.CAP,
    "4": Level.TERMINALE,
    "5": Level.BAC_2,
    "6": Level.BAC_3,
    "7": Level.BAC_5,
}

# Up to and including this level, a formation belongs to the secondary perimeter.
LAST_SECONDARY_LEVEL = 4


def certification_level_number(niveau: str | None) -> str:
    """Read a Carif-Oref level ("5 (BTS, DEUST...)" -> "5"), or "" when unreadable."""
    match = LEADING_NUMBER.match((niveau or "").strip())
    return match.group("number") if match else ""


def level_from_certification(number: str) -> str:
    """Translate a certification level ("5") into a `Level`, or "" when unknown."""
    return EXIT_LEVELS.get(number, "")


def is_secondary(number: str) -> bool:
    """Which perimeter a level belongs to. Only ever asked of a level `EXIT_LEVELS` knows."""
    return int(number) <= LAST_SECONDARY_LEVEL
