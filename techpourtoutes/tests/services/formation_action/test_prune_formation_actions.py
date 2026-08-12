import pytest

from techpourtoutes.models import Formation, FormationAction, School, TrainingExperience
from techpourtoutes.services.formation_action.prune_formation_actions import (
    PruneFormationActions,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def formation(db):
    formation = Formation(onisep_id="7118", name="Bac professionnel")
    formation.save()
    return formation


def test_an_action_missing_from_the_feed_is_deleted(formation, school):
    FormationAction(onisep_id="69395", formation=formation, school=school).save()

    result = PruneFormationActions(active_onisep_ids={"69396"})

    assert result.success
    assert FormationAction.objects.count() == 0


def test_an_action_still_in_the_feed_is_kept(formation, school):
    FormationAction(onisep_id="69395", formation=formation, school=school).save()

    PruneFormationActions(active_onisep_ids={"69395"})

    assert FormationAction.objects.get().onisep_id == "69395"


def test_an_action_a_parcours_relies_on_only_loses_its_identifier(formation, school, beneficiary):
    action = FormationAction(onisep_id="69395", formation=formation, school=school)
    action.save()
    TrainingExperience(user=beneficiary, school=school, formation=formation).save()

    PruneFormationActions(active_onisep_ids=set())

    action.refresh_from_db()
    assert action.onisep_id is None


def test_an_action_reached_through_the_parent_school_is_kept(
    formation, higher_ed_school, beneficiary
):
    affiliated = School(
        onisep_id="1967",
        name="EFREI Paris - campus de Villejuif",
        parent_onisep_id=higher_ed_school.onisep_id,
        higher_ed=True,
    )
    affiliated.save()
    action = FormationAction(onisep_id="69395", formation=formation, school=affiliated)
    action.save()
    TrainingExperience(user=beneficiary, school=higher_ed_school, formation=formation).save()

    PruneFormationActions(active_onisep_ids=set())

    action.refresh_from_db()
    assert action.onisep_id is None


def test_an_action_whose_formation_is_studied_elsewhere_is_deleted(
    formation, school, higher_ed_school, beneficiary
):
    FormationAction(onisep_id="69395", formation=formation, school=school).save()
    TrainingExperience(user=beneficiary, school=higher_ed_school, formation=formation).save()

    PruneFormationActions(active_onisep_ids=set())

    assert FormationAction.objects.count() == 0
