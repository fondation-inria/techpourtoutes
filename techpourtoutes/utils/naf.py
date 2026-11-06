import csv
from functools import cache

from django.conf import settings

# INSEE's list of the NAF rév. 2 sub-classes (naf2008_liste_n5.xls), codes without their dot.
NAF_PATH = settings.BASE_DIR / "data" / "naf" / "naf_rev2_sous_classes.csv"


def naf_label(code) -> str:
    """The INSEE label of a NAF sub-class spelled as the partners do (`4321A`); blank for a code
    the nomenclature does not list."""
    return _labels().get(code, "")


@cache
def _labels():
    with open(NAF_PATH, encoding="utf-8", newline="") as file:
        return {row["code"]: row["label"] for row in csv.DictReader(file)}
