import pytest
from django.core.management import call_command

from techpourtoutes.models import HigherEdSchool

HEADER = (
    "Etablissement,Siret,# adhérent,Conférence,UAI,Acronyme,"
    "Type de structure,Statut,Nom de marque,Type de formation,Commentaire,Campus"
)


def _write_csv(tmp_path, *rows):
    path = tmp_path / "higher_ed_schools.csv"
    path.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8")
    return str(path)


def _import(tmp_path, *rows):
    call_command("import_higher_ed_schools", path=_write_csv(tmp_path, *rows))


@pytest.mark.django_db
def test_collapses_multiline_full_name_and_strips_quotes(tmp_path):
    _import(
        tmp_path,
        '"Institut d\'enseignement\n  supérieur et de recherche",'
        '13000858400018,928,"CGE, CDEFI",0690193K,VetAgro Sup,EPSCP,Public,,Ingénieur,,',
    )

    school = HigherEdSchool.objects.get(uai="0690193K")
    assert school.full_name == "Institut d'enseignement supérieur et de recherche"


@pytest.mark.django_db
def test_maps_fields(tmp_path):
    _import(
        tmp_path,
        "VetAgro Sup établissement,13000858400018,928,CGE,0690193K,VetAgro Sup,,,,,,",
    )

    school = HigherEdSchool.objects.get(uai="0690193K")
    assert school.siret == "13000858400018"
    assert school.name == "VetAgro Sup"


@pytest.mark.django_db
def test_parses_conferences_into_list(tmp_path):
    _import(
        tmp_path,
        'UTT établissement,19101060200032,861,"CGE, CDEFI, FU",0101060Y,UTT,,,,,,',
    )

    assert HigherEdSchool.objects.get(uai="0101060Y").conferences == ["CGE", "CDEFI", "FU"]


@pytest.mark.django_db
def test_populates_normalized_fields(tmp_path):
    _import(
        tmp_path,
        "École supérieure établissement,12345678900011,1,FU,1234567A,Éésam,,,,,,",
    )

    school = HigherEdSchool.objects.get(uai="1234567A")
    assert school.full_name_normalized == "Ecole superieure etablissement"
    assert school.name_normalized == "Eesam"


@pytest.mark.django_db
def test_rerun_is_idempotent(tmp_path):
    row = "VetAgro Sup établissement,13000858400018,928,CGE,0690193K,VetAgro Sup,,,,,,"
    _import(tmp_path, row)
    _import(tmp_path, row)

    assert HigherEdSchool.objects.count() == 1


@pytest.mark.django_db
def test_deduplicates_by_uai_and_name(tmp_path):
    row = "Premier nom,13000858400018,928,CGE,0690193K,Premier,,,,,,"
    _import(tmp_path, row, row)

    assert HigherEdSchool.objects.count() == 1


@pytest.mark.django_db
def test_keeps_rows_sharing_uai_but_different_name(tmp_path):
    _import(
        tmp_path,
        "ISG établissement,78370705200032,1,CGE,0593202K,ISG,,,,,,",
        "IESEG établissement,78370705200032,2,CGE,0593202K,IESEG,,,,,,",
    )

    assert HigherEdSchool.objects.count() == 2


@pytest.mark.django_db
def test_deduplicates_by_siret_and_name(tmp_path):
    row = "Université des Antilles,19971585500011,,CDEFI,,Université des Antilles,,,,,,"
    _import(tmp_path, row, row)

    assert HigherEdSchool.objects.count() == 1


@pytest.mark.django_db
def test_keeps_rows_sharing_siret_but_different_name(tmp_path):
    _import(
        tmp_path,
        "Établissement A,19971585500011,,CDEFI,,Acronyme A,,,,,,",
        "Établissement B,19971585500011,,CDEFI,,Acronyme B,,,,,,",
    )

    assert HigherEdSchool.objects.count() == 2
