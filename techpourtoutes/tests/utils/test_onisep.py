import pytest

from techpourtoutes.models.level import Level
from techpourtoutes.utils.onisep import (
    domains_from_raw,
    duration_in_years,
    level_from_exit_level,
    onisep_id_from_url,
    read_onisep_csv,
    split_parent_label,
    sub_domains_from_raw,
)


def test_read_onisep_csv_yields_rows_keyed_by_the_onisep_json_keys():
    rows = read_onisep_csv("schools_secondary_sample.csv")

    assert len(rows) > 1
    assert {"url_et_id_onisep", "code_uai", "nom", "longitude_x"} <= rows[0].keys()


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.onisep.fr/http/redirection/formation/slug/FOR.9701", "9701"),
        ("https://www.onisep.fr/http/redirection/etablissement/slug/ENS.14008", "14008"),
        ("https://www.onisep.fr/http/redirection/formation/slug/AF.69395", "69395"),
        ("", ""),
        (None, ""),
    ],
)
def test_onisep_id_from_url(url, expected):
    assert onisep_id_from_url(url) == expected


def test_split_parent_label_extracts_name_and_uai():
    assert split_parent_label("Université de Reims Champagne-Ardenne (0511296G)") == (
        "Université de Reims Champagne-Ardenne",
        "0511296G",
    )


def test_split_parent_label_without_uai_keeps_the_name():
    assert split_parent_label("Université PSL") == ("Université PSL", "")


def test_split_parent_label_drops_everything_when_several_parents():
    value = "Nantes université (0442953W) | Le Mans université (0720916E)"

    assert split_parent_label(value) == ("", "")


def test_split_parent_label_of_an_empty_value():
    assert split_parent_label("") == ("", "")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("4E", Level.QUATRIEME),
        ("3E", Level.TROISIEME),
        ("seconde", Level.SECONDE),
        ("1re", Level.PREMIERE),
        ("CAP ou équivalent", Level.CAP),
        ("CAP ou équivalent + 1 an", Level.CAP_PLUS_1),
        ("bac ou équivalent", Level.TERMINALE),
        ("bac + 1", Level.BAC_1),
        ("bac + 5", Level.BAC_5),
        ("bac + 6", Level.BAC_6),
        ("bac + 8", Level.BAC_8),
        ("bac + 9 et plus", Level.BAC_9_PLUS),
        ("non renseigné", ""),
        ("", ""),
        ("valeur inattendue", ""),
    ],
)
def test_level_from_exit_level(raw, expected):
    assert level_from_exit_level(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [("1 an", 1), ("3 ans", 3), ("10 ans", 10), ("", None), (None, None), ("quelques mois", None)],
)
def test_duration_in_years(raw, expected):
    assert duration_in_years(raw) == expected


def test_domains_from_raw_splits_pairs_and_composite_domains():
    raw = "informatique, Internet/systèmes et réseaux | environnement, énergies, propreté/énergies"

    assert domains_from_raw(raw) == [
        "informatique",
        "Internet",
        "environnement",
        "énergies",
        "propreté",
    ]


def test_domains_from_raw_deduplicates():
    raw = "informatique, Internet/systèmes et réseaux | informatique, Internet/bases de données"

    assert domains_from_raw(raw) == ["informatique", "Internet"]


@pytest.mark.parametrize("raw", ["", None])
def test_domains_from_raw_of_an_empty_value(raw):
    assert domains_from_raw(raw) == []


def test_sub_domains_from_raw_splits_pairs():
    raw = "informatique, Internet/systèmes et réseaux | environnement, énergies, propreté/énergies"

    assert sub_domains_from_raw(raw) == ["systèmes et réseaux", "énergies"]


def test_sub_domains_from_raw_deduplicates():
    raw = "informatique, Internet/systèmes et réseaux | robotique/systèmes et réseaux"

    assert sub_domains_from_raw(raw) == ["systèmes et réseaux"]


@pytest.mark.parametrize("raw", ["", None])
def test_sub_domains_from_raw_of_an_empty_value(raw):
    assert sub_domains_from_raw(raw) == []
