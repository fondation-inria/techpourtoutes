import pytest

from techpourtoutes.models import Formation, FormationAction
from techpourtoutes.services.formation_action.upsert_formation_actions import (
    UpsertFormationActions,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def formation(db):
    formation = Formation(onisep_id="9701", name="diplôme d'ingénieur")
    formation.save()
    return formation


def test_import_links_a_formation_to_a_school(formation, school, formation_action_record):
    result = UpsertFormationActions(records=[formation_action_record(school_id=school.onisep_id)])

    assert result.success
    action = FormationAction.objects.get(onisep_id="69395")
    assert action.formation == formation
    assert action.school == school


def test_a_school_delivering_the_same_formation_twice_keeps_both_actions(
    formation, school, formation_action_record
):
    """383 (formation, school) pairs carry several AF ids."""
    records = [
        formation_action_record(onisep_id="69395", school_id=school.onisep_id),
        formation_action_record(onisep_id="69396", school_id=school.onisep_id),
    ]

    UpsertFormationActions(records=records)

    assert FormationAction.objects.count() == 2


def test_a_duplicated_action_id_is_imported_once(formation, school, formation_action_record):
    """115 AF ids appear twice in the source files."""
    records = [
        formation_action_record(school_id=school.onisep_id),
        formation_action_record(school_id=school.onisep_id),
    ]

    UpsertFormationActions(records=records)

    assert FormationAction.objects.count() == 1


def test_an_unknown_school_is_skipped(formation, formation_action_record):
    """7 ENS ids referenced by actions are absent from the Onisep structure files."""
    result = UpsertFormationActions(records=[formation_action_record(school_id="99999")])

    assert result.success
    assert FormationAction.objects.count() == 0


def test_an_unknown_formation_is_skipped(school, formation_action_record):
    result = UpsertFormationActions(
        records=[formation_action_record(formation_id="99999", school_id=school.onisep_id)]
    )

    assert result.success
    assert FormationAction.objects.count() == 0


def test_import_updates_an_existing_action_rather_than_duplicating_it(
    formation, school, formation_action_record
):
    other = Formation(onisep_id="9702", name="autre diplôme")
    other.save()
    UpsertFormationActions(records=[formation_action_record(school_id=school.onisep_id)])

    UpsertFormationActions(
        records=[formation_action_record(formation_id="9702", school_id=school.onisep_id)]
    )

    assert FormationAction.objects.count() == 1
    assert FormationAction.objects.get(onisep_id="69395").formation == other
