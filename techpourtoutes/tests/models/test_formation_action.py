import pytest
from django.core.exceptions import ValidationError

from techpourtoutes.models import Formation, FormationAction


@pytest.fixture
def formation(db):
    formation = Formation(onisep_id="9701", name="diplôme d'ingénieur")
    formation.save()
    return formation


@pytest.mark.django_db
def test_formation_action_onisep_id_is_unique(formation, school):
    FormationAction(onisep_id="69395", formation=formation, school=school).save()

    with pytest.raises(ValidationError):
        FormationAction(onisep_id="69395", formation=formation, school=school).save()


@pytest.mark.django_db
def test_a_school_delivers_the_same_formation_under_several_actions(formation, school):
    """383 (formation, school) pairs carry several AF ids: the pair must not be unique."""
    FormationAction(onisep_id="69395", formation=formation, school=school).save()
    FormationAction(onisep_id="69396", formation=formation, school=school).save()

    assert formation.actions.count() == 2
    assert list(formation.schools.all()) == [school, school]


@pytest.mark.django_db
def test_formation_action_str_shows_both_ends(formation, school):
    action = FormationAction(onisep_id="69395", formation=formation, school=school)
    action.save()

    assert str(action) == f"{formation.name} – {school.name}"
