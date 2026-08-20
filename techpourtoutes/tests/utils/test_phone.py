import pytest

from techpourtoutes.utils.phone import parse_phone


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("04 76 82 72 00", "+33476827200"),
        ("01 44 41 57 41", "+33144415741"),
        ("02 62 35 44 35", "+262262354435"),  # La Réunion
        ("05 90 82 15 89", "+590590821589"),  # Guadeloupe
        ("05 94 30 34 39", "+594594303439"),  # Guyane
    ],
)
def test_parse_phone_returns_e164(raw, expected):
    assert parse_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "39 36", "30 06", "03 81 39 33 00 55", "n/a"])
def test_parse_phone_drops_unusable_values(raw):
    assert parse_phone(raw) == ""


def test_parse_phone_accepts_none():
    assert parse_phone(None) == ""
