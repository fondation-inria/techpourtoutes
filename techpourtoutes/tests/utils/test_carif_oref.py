import pytest

from techpourtoutes.models.level import Level
from techpourtoutes.utils.carif_oref import (
    certification_level_number,
    is_secondary,
    level_from_certification,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("3 (CAP...)", "3"),
        ("4 (BAC...)", "4"),
        ("5 (BTS, DEUST...)", "5"),
        ("6 (Licence, BUT...)", "6"),
        ("7 (Master, titre ingénieur...)", "7"),
        ("", ""),
        (None, ""),
        ("indéterminé", ""),
    ],
)
def test_certification_level_number(raw, expected):
    assert certification_level_number(raw) == expected


@pytest.mark.parametrize(
    "number,expected",
    [
        ("3", Level.CAP),
        ("4", Level.TERMINALE),
        ("5", Level.BAC_2),
        ("6", Level.BAC_3),
        ("7", Level.BAC_5),
        ("", ""),
        ("9", ""),
    ],
)
def test_level_from_certification(number, expected):
    assert level_from_certification(number) == expected


@pytest.mark.parametrize(
    "number,expected", [("3", True), ("4", True), ("5", False), ("6", False), ("7", False)]
)
def test_is_secondary_splits_the_two_perimeters(number, expected):
    assert is_secondary(number) is expected
