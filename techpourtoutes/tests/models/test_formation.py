import pytest
from django.core.exceptions import ValidationError

from techpourtoutes.models import Formation, FormationAction, School
from techpourtoutes.models.level import Level


@pytest.mark.django_db
def test_formation_str_shows_the_name():
    formation = Formation(onisep_id="9701", name="diplôme d'ingénieur du CESI")
    formation.save()

    assert str(formation) == "diplôme d'ingénieur du CESI"


@pytest.mark.django_db
def test_formation_onisep_id_is_unique():
    Formation(onisep_id="9701", name="diplôme d'ingénieur").save()

    with pytest.raises(ValidationError):
        Formation(onisep_id="9701", name="autre diplôme").save()


@pytest.mark.django_db
def test_formation_accepts_a_level_beyond_the_beneficiary_funnel():
    formation = Formation(onisep_id="9701", name="mastère spécialisé", exit_level=Level.BAC_6)
    formation.save()

    assert Formation.objects.get(onisep_id="9701").exit_level == Level.BAC_6


@pytest.mark.django_db
def test_formation_lists_the_schools_that_deliver_it(school):
    formation = Formation(onisep_id="9701", name="diplôme d'ingénieur")
    formation.save()
    FormationAction(onisep_id="69395", formation=formation, school=school).save()

    assert list(formation.schools.all()) == [school]
    assert list(school.formations.all()) == [formation]


@pytest.mark.django_db
def test_formation_save_populates_the_normalized_name():
    formation = Formation(onisep_id="9701", name="Diplôme d'État d'infirmier")
    formation.save()

    assert formation.name_normalized == "Diplome d'Etat d'infirmier"


@pytest.mark.django_db
def test_formation_search_ignores_accents_and_narrows_on_every_token():
    Formation(onisep_id="1", name="Diplôme d'État d'infirmier").save()
    Formation(onisep_id="2", name="Diplôme d'État d'auxiliaire de puériculture").save()

    assert [
        formation.onisep_id for formation in Formation.objects.search("diplome etat infirmier")
    ] == ["1"]


@pytest.mark.django_db
def test_formation_search_without_a_query_keeps_everything():
    Formation(onisep_id="1", name="Diplôme d'État d'infirmier").save()

    assert Formation.objects.search("").count() == 1


@pytest.mark.django_db
def test_taught_at_lists_what_the_school_teaches(school):
    taught = Formation(onisep_id="1", name="Bac professionnel")
    taught.save()
    Formation(onisep_id="2", name="Diplôme d'ingénieur").save()
    FormationAction(onisep_id="69395", formation=taught, school=school).save()

    assert list(Formation.objects.taught_at(school)) == [taught]


@pytest.mark.django_db
def test_taught_at_includes_the_formations_of_the_affiliated_schools(higher_ed_school):
    affiliated = School(
        onisep_id="1967",
        name="EFREI Paris - campus de Villejuif",
        parent_onisep_id=higher_ed_school.onisep_id,
        higher_ed=True,
    )
    affiliated.save()
    formation = Formation(onisep_id="1", name="Diplôme d'ingénieur")
    formation.save()
    FormationAction(onisep_id="69395", formation=formation, school=affiliated).save()

    assert list(Formation.objects.taught_at(higher_ed_school)) == [formation]


@pytest.mark.django_db
def test_taught_at_lists_a_formation_once_whatever_its_number_of_actions(school):
    formation = Formation(onisep_id="1", name="Bac professionnel")
    formation.save()
    FormationAction(onisep_id="69395", formation=formation, school=school).save()
    FormationAction(onisep_id="69396", formation=formation, school=school).save()

    assert list(Formation.objects.taught_at(school)) == [formation]


@pytest.mark.django_db
def test_taught_at_falls_back_to_the_whole_catalogue_when_the_school_teaches_nothing(school):
    Formation(onisep_id="1", name="Bac professionnel").save()
    Formation(onisep_id="2", name="Diplôme d'ingénieur").save()

    assert Formation.objects.taught_at(school).count() == 2


@pytest.mark.django_db
def test_taught_at_before_search_keeps_an_unmatched_query_empty(school):
    taught = Formation(onisep_id="1", name="Bac professionnel")
    taught.save()
    Formation(onisep_id="2", name="Diplôme d'ingénieur").save()
    FormationAction(onisep_id="69395", formation=taught, school=school).save()

    assert not Formation.objects.taught_at(school).search("ingénieur").exists()
