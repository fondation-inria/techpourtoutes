import pytest

from techpourtoutes.models import School
from techpourtoutes.services.school.upsert_schools import UpsertSchools

pytestmark = pytest.mark.django_db


def test_import_maps_every_kept_column(school_record):
    result = UpsertSchools(records=[school_record()], scope="higher_ed")

    assert result.success
    school = School.objects.get(onisep_id="14008")
    assert school.uai == "0383399N"
    assert school.siret == "19381912500231"
    assert school.type == "école d'ingénieurs"
    assert school.name == "École nationale supérieure d'informatique"
    assert school.acronym == "Ensimag"
    assert school.status == "public"
    assert school.mailbox == "BP 72"
    assert school.address == "681 rue de la Passerelle"
    assert school.postal_code == "38402"
    assert school.city == "Saint-Martin-d'Hères"
    assert school.cog_code == "38421"
    assert school.cedex == "Cedex"
    assert school.phone == "+33476827200"
    assert school.department == "38 - Isère"
    assert school.academy == "Grenoble"
    assert school.region == "Auvergne-Rhône-Alpes"
    assert school.region_code == "84"
    assert school.longitude == 5.76804
    assert school.latitude == 45.1935
    assert school.name_normalized == "Ecole nationale superieure d'informatique"


def test_import_flags_the_scope(school_record):
    UpsertSchools(records=[school_record()], scope="secondary")

    school = School.objects.get(onisep_id="14008")
    assert school.secondary
    assert not school.higher_ed


def test_a_school_in_both_files_carries_both_flags(school_record):
    """4 261 établissements appear in both Onisep structure files."""
    UpsertSchools(records=[school_record()], scope="secondary")
    UpsertSchools(records=[school_record()], scope="higher_ed")

    school = School.objects.get(onisep_id="14008")
    assert school.secondary
    assert school.higher_ed


def test_the_other_order_gives_the_same_flags(school_record):
    UpsertSchools(records=[school_record()], scope="higher_ed")
    UpsertSchools(records=[school_record()], scope="secondary")

    school = School.objects.get(onisep_id="14008")
    assert school.secondary
    assert school.higher_ed


def test_import_never_clears_the_training_ambassador_flag(school_record):
    UpsertSchools(records=[school_record()], scope="higher_ed")
    School.objects.filter(onisep_id="14008").update(training_ambassador_eligible=True)

    UpsertSchools(records=[school_record(nom="Nouveau nom")], scope="higher_ed")

    school = School.objects.get(onisep_id="14008")
    assert school.training_ambassador_eligible
    assert school.name == "Nouveau nom"


def test_import_updates_an_existing_school_rather_than_duplicating_it(school_record):
    UpsertSchools(records=[school_record()], scope="higher_ed")
    UpsertSchools(records=[school_record(cp="75011")], scope="higher_ed")

    assert School.objects.count() == 1
    assert School.objects.get(onisep_id="14008").postal_code == "75011"


def test_a_parent_university_prefixes_the_name(school_record):
    record = school_record(
        nom="Campus des Comtes de Champagne",
        universite_de_rattachement_libelle_et_uai=(
            "Université de Reims Champagne-Ardenne (0511296G)"
        ),
        universite_de_rattachement_id_et_url_onisep=(
            "https://www.onisep.fr/http/redirection/etablissement/slug/ENS.490"
        ),
    )

    UpsertSchools(records=[record], scope="higher_ed")

    school = School.objects.get(onisep_id="14008")
    assert school.name == "Université de Reims Champagne-Ardenne - Campus des Comtes de Champagne"
    assert school.parent_uai == "0511296G"
    assert school.parent_onisep_id == "490"


def test_a_parent_without_a_uai_still_prefixes_the_name(school_record):
    record = school_record(
        nom="École des mines de Paris",
        universite_de_rattachement_libelle_et_uai="Université PSL",
        universite_de_rattachement_id_et_url_onisep=(
            "https://www.onisep.fr/http/redirection/etablissement/slug/ENS.729"
        ),
    )

    UpsertSchools(records=[record], scope="higher_ed")

    school = School.objects.get(onisep_id="14008")
    assert school.name == "Université PSL - École des mines de Paris"
    assert school.parent_uai == ""
    assert school.parent_onisep_id == "729"


def test_several_parents_claim_none_of_them(school_record):
    record = school_record(
        nom="INSPE site de Laval",
        universite_de_rattachement_libelle_et_uai=(
            "Nantes université (0442953W) | Le Mans université (0720916E)"
        ),
        universite_de_rattachement_id_et_url_onisep=(
            "https://www.onisep.fr/http/redirection/etablissement/slug/ENS.106 | "
            "https://www.onisep.fr/http/redirection/etablissement/slug/ENS.378"
        ),
    )

    UpsertSchools(records=[record], scope="higher_ed")

    school = School.objects.get(onisep_id="14008")
    assert school.name == "INSPE site de Laval"
    assert school.parent_uai == ""
    assert school.parent_onisep_id == ""


def test_an_undiallable_phone_is_dropped(school_record):
    UpsertSchools(records=[school_record(telephone="39 36")], scope="higher_ed")

    assert School.objects.get(onisep_id="14008").phone == ""


def test_missing_coordinates_stay_empty(school_record):
    UpsertSchools(records=[school_record(longitude_x="", latitude_y="")], scope="higher_ed")

    school = School.objects.get(onisep_id="14008")
    assert school.longitude is None
    assert school.latitude is None


def test_coordinates_read_from_a_csv_are_coerced(school_record):
    """The seed samples come from CSV, where every value is a string."""
    UpsertSchools(
        records=[school_record(longitude_x="5.76804", latitude_y="45.1935")], scope="higher_ed"
    )

    school = School.objects.get(onisep_id="14008")
    assert school.longitude == 5.76804
    assert school.latitude == 45.1935


def test_records_repeated_in_one_file_are_deduplicated(school_record):
    UpsertSchools(
        records=[school_record(), school_record(nom="Le dernier gagne")], scope="higher_ed"
    )

    assert School.objects.count() == 1
    assert School.objects.get(onisep_id="14008").name == "Le dernier gagne"


def test_a_record_without_an_identifier_is_skipped(school_record):
    UpsertSchools(records=[school_record(url_et_id_onisep=""), school_record()], scope="higher_ed")

    assert School.objects.count() == 1


def test_an_unknown_scope_fails(school_record):
    result = UpsertSchools(records=[school_record()], scope="inconnu")

    assert result.failure
    assert School.objects.count() == 0
