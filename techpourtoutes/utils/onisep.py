import csv
import re

from django.conf import settings

from techpourtoutes.models.level import Level

ONISEP_DATA_DIR = settings.BASE_DIR / "data" / "onisep"

PARENT_WITH_UAI = re.compile(r"(?P<name>.*?)\s*\((?P<uai>[^()]+)\)")
DURATION = re.compile(r"(?P<years>\d+)\s+ans?")

EXIT_LEVELS = {
    "4e": Level.QUATRIEME,
    "3e": Level.TROISIEME,
    "seconde": Level.SECONDE,
    "1re": Level.PREMIERE,
    "cap ou équivalent": Level.CAP,
    "cap ou équivalent + 1 an": Level.CAP_PLUS_1,
    "bac ou équivalent": Level.TERMINALE,
    "bac + 1": Level.BAC_1,
    "bac + 2": Level.BAC_2,
    "bac + 3": Level.BAC_3,
    "bac + 4": Level.BAC_4,
    "bac + 5": Level.BAC_5,
    "bac + 6": Level.BAC_6,
    "bac + 7": Level.BAC_7,
    "bac + 8": Level.BAC_8,
    "bac + 9 et plus": Level.BAC_9_PLUS,
}


def read_onisep_csv(filename: str) -> list[dict]:
    """The committed CSV headers are the Onisep JSON keys, so a file and the API yield the
    very same dicts — one mapper serves both."""
    with open(ONISEP_DATA_DIR / filename, encoding="utf-8") as file:
        return list(csv.DictReader(file))


def onisep_id_from_url(url: str | None) -> str:
    """Keep the trailing id of an Onisep link (".../slug/FOR.9701" -> "9701")."""
    return url.rsplit(".", 1)[-1] if url else ""


def split_parent_label(value: str | None) -> tuple[str, str]:
    """Read a parent university as ("Université de Reims Champagne-Ardenne", "0511296G").
    Some schools list several parents ("A (uai) | B (uai)"): we then claim none of them,
    because the name is explicit enough in those cases.
    """
    if not value or "|" in value:
        return "", ""
    match = PARENT_WITH_UAI.fullmatch(value.strip())
    return match.group("name", "uai") if match else (value.strip(), "")


def level_from_exit_level(value: str | None) -> str:
    """Translate an Onisep exit level ("bac + 6") into a `Level`, or "" when unknown."""
    return EXIT_LEVELS.get((value or "").strip().lower(), "")


def duration_in_years(value: str | None) -> int | None:
    """Read a formation duration ("3 ans" -> 3). Onisep only ever expresses it in years."""
    match = DURATION.fullmatch((value or "").strip())
    return int(match.group("years")) if match else None
