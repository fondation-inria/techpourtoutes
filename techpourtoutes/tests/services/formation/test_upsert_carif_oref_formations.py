import pytest

from techpourtoutes.models import Formation, FormationAction, School
from techpourtoutes.models.level import Level
from techpourtoutes.services.formation.upsert_carif_oref_formations import (
    UpsertCarifOrefFormations,
)

pytestmark = pytest.mark.django_db

SIRET = "38855948600070"
UAI = "0681832X"


@pytest.fixture
def cfa(db):
    """The établissement the record fixture points at, by both of its identifiers."""
    school = School(onisep_id="1967", name="CFAI Alsace", siret=SIRET, uai=UAI, higher_ed=True)
    school.save()
    return school


def test_a_formation_the_catalogue_alone_knows_is_created(cfa, carif_oref_record):
    result = UpsertCarifOrefFormations(records=[carif_oref_record()])

    assert result.success
    formation = Formation.objects.get(onisep_id="5978")
    assert formation.code_nsf == "254"
    assert formation.type_name == "Brevet de technicien supérieur"
    assert formation.type_acronym == "BTS"
    assert formation.name == "BTS conception des processus de réalisation de produits"
    assert formation.name_normalized == "BTS conception des processus de realisation de produits"
    assert formation.duration_in_years == 2
    assert formation.exit_level == Level.BAC_2
    assert formation.certification_level_name == "niveau 5"
    assert formation.higher_ed is True
    assert formation.secondary is False


def test_the_onisep_only_columns_stay_empty(cfa, carif_oref_record):
    """`certification_level` is an Onisep-internal code, not the RNCP level."""
    UpsertCarifOrefFormations(records=[carif_oref_record()])

    formation = Formation.objects.get(onisep_id="5978")
    assert formation.certification_level == ""
    assert formation.code_scolarite == ""
    assert formation.code_rncp == ""


def test_a_secondary_level_flags_the_formation_the_other_way(cfa, carif_oref_record):
    UpsertCarifOrefFormations(records=[carif_oref_record(niveau="3 (CAP...)")])

    formation = Formation.objects.get(onisep_id="5978")
    assert formation.exit_level == Level.CAP
    assert formation.secondary is True
    assert formation.higher_ed is False


def test_a_type_acronym_longer_than_onisep_ever_sends_fits(cfa, carif_oref_record):
    record = carif_oref_record(
        rncp_details={"code_type_certif": "Licence Professionnelle", "type_certif": None}
    )

    UpsertCarifOrefFormations(records=[record])

    assert Formation.objects.get(onisep_id="5978").type_acronym == "Licence Professionnelle"


def test_the_formation_is_linked_to_the_school(cfa, carif_oref_record):
    UpsertCarifOrefFormations(records=[carif_oref_record()])

    link = FormationAction.objects.get()
    assert link.school == cfa
    assert link.formation.onisep_id == "5978"
    assert link.onisep_id is None


def test_the_school_gains_the_perimeter_without_losing_the_other(cfa, carif_oref_record):
    cfa.secondary = True
    cfa.save()

    UpsertCarifOrefFormations(records=[carif_oref_record()])

    cfa.refresh_from_db()
    assert cfa.higher_ed is True
    assert cfa.secondary is True


def test_a_school_of_the_other_perimeter_gains_the_flag(cfa, carif_oref_record):
    cfa.higher_ed = False
    cfa.secondary = True
    cfa.save()

    UpsertCarifOrefFormations(records=[carif_oref_record()])

    cfa.refresh_from_db()
    assert cfa.higher_ed is True


def test_a_formation_onisep_already_describes_is_left_untouched(cfa, carif_oref_record):
    Formation(onisep_id="5978", name="Le libellé Onisep", code_rncp="37464").save()

    UpsertCarifOrefFormations(records=[carif_oref_record()])

    formation = Formation.objects.get(onisep_id="5978")
    assert formation.name == "Le libellé Onisep"
    assert formation.code_rncp == "37464"
    assert formation.type_acronym == ""
    assert FormationAction.objects.filter(formation=formation, school=cfa).exists()


def test_a_record_whose_school_is_unknown_is_skipped(carif_oref_record):
    result = UpsertCarifOrefFormations(records=[carif_oref_record()])

    assert result.success
    assert Formation.objects.count() == 0
    assert FormationAction.objects.count() == 0


def test_a_record_without_an_onisep_link_is_skipped(cfa, carif_oref_record):
    UpsertCarifOrefFormations(records=[carif_oref_record(onisep_url=None)])

    assert Formation.objects.count() == 0


def test_a_record_whose_level_is_unreadable_is_skipped(cfa, carif_oref_record):
    UpsertCarifOrefFormations(records=[carif_oref_record(niveau="indéterminé")])

    assert Formation.objects.count() == 0


def test_running_twice_creates_nothing_the_second_time(cfa, carif_oref_record):
    UpsertCarifOrefFormations(records=[carif_oref_record()])
    UpsertCarifOrefFormations(records=[carif_oref_record()])

    assert Formation.objects.count() == 1
    assert FormationAction.objects.count() == 1


def test_a_link_onisep_already_carries_is_not_duplicated(cfa, carif_oref_record):
    formation = Formation(onisep_id="5978", name="Le libellé Onisep")
    formation.save()
    FormationAction(onisep_id="69395", formation=formation, school=cfa).save()

    UpsertCarifOrefFormations(records=[carif_oref_record()])

    assert FormationAction.objects.count() == 1


def test_the_same_formation_taught_in_two_places_is_linked_to_both(cfa, carif_oref_record):
    other = School(onisep_id="1968", name="CFAI Mulhouse", siret="11111111111111", uai="0680001Z")
    other.save()
    elsewhere = carif_oref_record(
        etablissement_formateur_siret=other.siret,
        etablissement_formateur_uai=other.uai,
        etablissement_gestionnaire_siret=other.siret,
        etablissement_gestionnaire_uai=other.uai,
    )

    UpsertCarifOrefFormations(records=[carif_oref_record(), elsewhere])

    assert Formation.objects.count() == 1
    assert FormationAction.objects.count() == 2


def test_records_repeated_in_one_page_are_deduplicated(cfa, carif_oref_record):
    UpsertCarifOrefFormations(records=[carif_oref_record(), carif_oref_record()])

    assert Formation.objects.count() == 1
    assert FormationAction.objects.count() == 1


def _linked_school_names():
    return sorted(link.school.name for link in FormationAction.objects.select_related("school"))


def test_both_identifiers_are_preferred_over_either_alone(cfa, carif_oref_record):
    """A SIRET is shared by every site of one legal entity: the pair is the sharpest key."""
    School(onisep_id="1968", name="Autre site", siret=SIRET, uai="0670001A").save()

    UpsertCarifOrefFormations(records=[carif_oref_record()])

    assert _linked_school_names() == ["CFAI Alsace"]


def test_the_uai_alone_catches_a_school_whose_siret_differs(carif_oref_record):
    School(onisep_id="1968", name="Même UAI", siret="99999999999999", uai=UAI).save()

    UpsertCarifOrefFormations(records=[carif_oref_record()])

    assert _linked_school_names() == ["Même UAI"]


def test_the_siret_alone_catches_a_school_without_a_uai(carif_oref_record):
    School(onisep_id="1968", name="Sans UAI", siret=SIRET, uai="").save()

    UpsertCarifOrefFormations(records=[carif_oref_record()])

    assert _linked_school_names() == ["Sans UAI"]


def test_the_uai_is_tried_before_the_siret(carif_oref_record):
    School(onisep_id="1968", name="Même UAI", siret="99999999999999", uai=UAI).save()
    School(onisep_id="1969", name="Même SIRET", siret=SIRET, uai="0670001A").save()

    UpsertCarifOrefFormations(records=[carif_oref_record()])

    assert _linked_school_names() == ["Même UAI"]


def test_the_gestionnaire_is_tried_once_the_formateur_matches_nothing(carif_oref_record):
    School(onisep_id="1968", name="Le gestionnaire", siret="11111111111111", uai="0680001Z").save()
    record = carif_oref_record(
        etablissement_formateur_siret="00000000000000",
        etablissement_formateur_uai="0000000X",
        etablissement_gestionnaire_siret="11111111111111",
        etablissement_gestionnaire_uai="0680001Z",
    )

    UpsertCarifOrefFormations(records=[record])

    assert _linked_school_names() == ["Le gestionnaire"]


def test_several_schools_sharing_a_key_are_all_linked(carif_oref_record):
    School(onisep_id="1968", name="Site A", siret=SIRET, uai=UAI).save()
    School(onisep_id="1969", name="Site B", siret=SIRET, uai=UAI).save()

    UpsertCarifOrefFormations(records=[carif_oref_record()])

    assert _linked_school_names() == ["Site A", "Site B"]


def test_a_school_without_identifiers_is_never_matched_by_a_blank_key(carif_oref_record):
    School(onisep_id="1968", name="Ni SIRET ni UAI", siret="", uai="").save()
    record = carif_oref_record(
        etablissement_formateur_siret="",
        etablissement_formateur_uai=None,
        etablissement_gestionnaire_siret="",
        etablissement_gestionnaire_uai=None,
    )

    UpsertCarifOrefFormations(records=[record])

    assert FormationAction.objects.count() == 0
