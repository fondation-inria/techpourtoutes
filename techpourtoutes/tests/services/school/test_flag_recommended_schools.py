import pytest

from techpourtoutes.models import Formation
from techpourtoutes.models.formation_action import FormationAction
from techpourtoutes.models.school import School
from techpourtoutes.services.school.flag_recommended_schools import FlagRecommendedSchools

pytestmark = pytest.mark.django_db

SCHOOL_ONISEP_ID = "13362"


@pytest.fixture
def school(db):
    school = School(
        onisep_id=SCHOOL_ONISEP_ID,
        name=f"Établissement {SCHOOL_ONISEP_ID}",
        higher_ed=False,
        type="lycée professionnel",
        status="public",
    )
    school.save()
    return school


@pytest.fixture
def formation(db):
    formation = Formation(onisep_id="7118", name="Bac CIEL", acronym="CIEL", secondary=True)
    formation.save()
    return formation


@pytest.fixture
def formation_action(db, formation, school):
    FormationAction(formation=formation, school=school).save()


def test_recommended_school_is_flagged(school, formation, formation_action):
    result = FlagRecommendedSchools()

    assert result.success
    assert School.objects.get(onisep_id=SCHOOL_ONISEP_ID).recommended


def test_unrecommended_school_is_flagged(school):
    unrecommended_school = School(onisep_id="0000", name="Lycée truc", higher_ed=False)
    unrecommended_school.save()
    unrecommended_formation = Formation(
        onisep_id="7118", name="Bac littéraire", acronym="L", secondary=True
    )
    unrecommended_formation.save()
    FormationAction(formation=unrecommended_formation, school=unrecommended_school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert not School.objects.get(onisep_id="0000").recommended


@pytest.mark.parametrize("bac_techno_code", ["STMG", "STI2D", "STL"])
def test_technological_school_teaching_the_bac_techno_is_flagged(bac_techno_code):
    school = School(
        onisep_id="10408",
        name="Lycée général et technologique privé Jeanne d'Arc",
        higher_ed=False,
        type="lycée général, technologique ou polyvalent",
        status="privé sous contrat",
    )
    school.save()
    formation = Formation(
        onisep_id=f"bac-{bac_techno_code}",
        name=f"Bac techno {bac_techno_code} sciences et technologies",
        type_name="baccalauréat technologique",
        secondary=True,
    )
    formation.save()
    FormationAction(formation=formation, school=school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert School.objects.get(onisep_id="10408").recommended


def test_technological_school_teaching_a_different_bac_techno_is_not_flagged():
    school = School(
        onisep_id="20000",
        name="Lycée sans STMG",
        higher_ed=False,
        type="lycée général, technologique ou polyvalent",
        status="public",
    )
    school.save()
    formation = Formation(
        onisep_id="bac-st2s",
        name="Bac techno ST2S sciences et technologies de la santé et du social",
        type_name="baccalauréat technologique",
        secondary=True,
    )
    formation.save()
    FormationAction(formation=formation, school=school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert not School.objects.get(onisep_id="20000").recommended


def test_lycee_pro_teaching_stmg_is_flagged():
    school = School(
        onisep_id="30000",
        name="Lycée pro avec STMG",
        higher_ed=False,
        type="lycée professionnel",
        status="public",
    )
    school.save()
    formation = Formation(
        onisep_id="bac-stmg-pro",
        name="Bac techno STMG sciences et technologies du management et de la gestion",
        type_name="baccalauréat technologique",
        secondary=True,
    )
    formation.save()
    FormationAction(formation=formation, school=school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert School.objects.get(onisep_id="30000").recommended


@pytest.mark.parametrize("cpge_track", ["MPSI", "BCPST", "TPC"])
def test_school_teaching_the_cpge_track_is_flagged(cpge_track):
    school = School(onisep_id="40000", name="Lycée avec prépa", status="public")
    school.save()
    formation = Formation(
        onisep_id=f"cpge-{cpge_track}",
        name=f"Classe préparatoire {cpge_track}, 1re année",
        type_acronym="CPGE",
        type_name="classe préparatoire scientifique et technologique",
    )
    formation.save()
    FormationAction(formation=formation, school=school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert School.objects.get(onisep_id="40000").recommended


def test_school_teaching_a_literary_cpge_is_not_flagged():
    school = School(onisep_id="50000", name="Lycée avec prépa littéraire", status="public")
    school.save()
    formation = Formation(
        onisep_id="cpge-lettres",
        name="Classe préparatoire de lettres (1re année)",
        type_acronym="CPGE",
        type_name="classe préparatoire littéraire et artistique",
    )
    formation.save()
    FormationAction(formation=formation, school=school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert not School.objects.get(onisep_id="50000").recommended


def test_school_teaching_a_scientific_cpge_outside_the_track_list_is_not_flagged():
    school = School(onisep_id="60000", name="Lycée avec prépa TB", status="public")
    school.save()
    formation = Formation(
        onisep_id="cpge-tb",
        name="Classe préparatoire technologie et biologie (TB), 1re année",
        type_acronym="CPGE",
        type_name="classe préparatoire scientifique et technologique",
    )
    formation.save()
    FormationAction(formation=formation, school=school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert not School.objects.get(onisep_id="60000").recommended


def test_training_ambassador_school_is_flagged():
    School(
        onisep_id="70000",
        name="Établissement ambassadrice",
        status="public",
        training_ambassador_eligible=True,
    ).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert School.objects.get(onisep_id="70000").recommended


@pytest.mark.parametrize(
    "type_", ["lycée professionnel", "lycée général, technologique ou polyvalent"]
)
def test_lycee_teaching_a_computer_science_formation_is_flagged(type_):
    school = School(onisep_id="80000", name="Lycée avec BTS SIO", status="public", type=type_)
    school.save()
    formation = Formation(
        onisep_id="bts-sio",
        name="BTS services informatiques aux organisations",
        domains=["informatique", "Internet"],
        sub_domains=["systèmes et réseaux"],
    )
    formation.save()
    FormationAction(formation=formation, school=school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert School.objects.get(onisep_id="80000").recommended


def test_lycee_teaching_an_electronics_formation_is_flagged():
    school = School(
        onisep_id="120000",
        name="Lycée avec bac STI2D SIN",
        status="public",
        type="lycée général, technologique ou polyvalent",
    )
    school.save()
    formation = Formation(
        onisep_id="bac-electronique",
        name="Bac STI2D systèmes d'information et numérique",
        domains=["électricité", "électronique", "robotique"],
        sub_domains=["électrotechnique"],
    )
    formation.save()
    FormationAction(formation=formation, school=school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert School.objects.get(onisep_id="120000").recommended


def test_lycee_teaching_administrateur_reseau_is_flagged_even_without_the_domain():
    school = School(
        onisep_id="90000",
        name="Lycée avec FCIL administrateur réseau",
        status="public",
        type="lycée professionnel",
    )
    school.save()
    formation = Formation(
        onisep_id="fcil-admin-reseau",
        name="FCIL administrateur réseau, infrastructure et système numérique",
        domains=["information-communication", "audiovisuel"],
        sub_domains=["multimédia"],
    )
    formation.save()
    FormationAction(formation=formation, school=school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert School.objects.get(onisep_id="90000").recommended


def test_non_lycee_teaching_a_computer_science_formation_is_not_flagged():
    school = School(
        onisep_id="100000",
        name="École supérieure privée",
        status="public",
        type="autre établissement d'enseignement",
    )
    school.save()
    formation = Formation(
        onisep_id="bts-sio-2",
        name="BTS services informatiques aux organisations",
        domains=["informatique", "Internet"],
        sub_domains=["systèmes et réseaux"],
    )
    formation.save()
    FormationAction(formation=formation, school=school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert not School.objects.get(onisep_id="100000").recommended


def test_lycee_teaching_an_unrelated_formation_is_not_flagged():
    school = School(
        onisep_id="110000",
        name="Lycée avec BTS géomètre-topographe",
        status="public",
        type="lycée général, technologique ou polyvalent",
    )
    school.save()
    formation = Formation(
        onisep_id="bts-geometre",
        name="BTS métiers du géomètre-topographe et de la modélisation numérique",
        domains=["construction", "architecture", "travaux publics"],
        sub_domains=["bureau d'études BTP"],
    )
    formation.save()
    FormationAction(formation=formation, school=school).save()

    result = FlagRecommendedSchools()

    assert result.success
    assert not School.objects.get(onisep_id="110000").recommended
