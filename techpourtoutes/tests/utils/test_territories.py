import pytest

from techpourtoutes.utils.territories import department_code


@pytest.mark.parametrize(
    "cog_code, postal_code, expected",
    [
        ("29019", "", "29"),
        ("2A004", "", "2A"),
        ("97411", "", "974"),
        ("99132", "", "99"),
        ("", "29000", "29"),
        ("", "20137", "2A"),
        ("", "20200", "2B"),
        ("", "97410", "974"),
        ("75056", "13001", "75"),
        ("98818", "", "988"),
        ("97701", "", "977"),
        ("", "98800", "988"),
        ("", "00000", ""),
        ("", "", ""),
    ],
)
def test_department_code_reads_the_cog_first_then_the_postal_code(cog_code, postal_code, expected):
    assert department_code(cog_code, postal_code) == expected
