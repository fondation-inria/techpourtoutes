from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.models import Formation, FormationAction, School
from techpourtoutes.services.formation.import_formations import ImportFormations
from techpourtoutes.services.formation_action.import_formation_actions import (
    ImportFormationActions,
)
from techpourtoutes.services.school.import_schools import ImportSchools

pytestmark = pytest.mark.django_db

FETCH = (
    "techpourtoutes.services.formation_action.import_formation_actions.FetchOnisepFormationActions"
)


def _obsolete_action():
    """A link the feed used to carry, on two rows the samples do provide."""
    action = FormationAction(
        onisep_id="obsolete",
        formation=Formation.objects.first(),
        school=School.objects.first(),
    )
    action.save()
    return action


@pytest.fixture
def both_ends(db):
    """Actions need their formation and their établissement in place beforehand."""
    ImportSchools(sample=True)
    ImportFormations(sample=True)


def test_the_samples_are_read_without_touching_the_network(both_ends):
    with patch(FETCH) as fetch:
        result = ImportFormationActions(sample=True)

    fetch.assert_not_called()
    assert result.success
    assert FormationAction.objects.count() == 200


def test_a_single_scope_imports_half_of_them(both_ends):
    ImportFormationActions(scope="lycee", sample=True)

    assert FormationAction.objects.count() == 100


def test_a_single_scope_flags_the_linked_formations(both_ends):
    ImportFormationActions(scope="lycee", sample=True)

    linked_formations = Formation.objects.filter(actions__isnull=False).distinct()
    assert linked_formations.exists()
    assert not linked_formations.filter(secondary=False).exists()


def test_without_a_sample_each_scope_is_downloaded(both_ends, formation_action_record):
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(failure=False, onisep_records=[])
        ImportFormationActions()

    assert [call.kwargs["scope"] for call in fetch.call_args_list] == ["lycee", "superieur"]


def test_a_full_download_prunes_the_links_the_feed_no_longer_carries(both_ends):
    _obsolete_action()

    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(failure=False, onisep_records=[])
        ImportFormationActions()

    assert not FormationAction.objects.filter(onisep_id="obsolete").exists()


def test_a_sample_import_never_prunes(both_ends):
    _obsolete_action()

    ImportFormationActions(sample=True)

    assert FormationAction.objects.filter(onisep_id="obsolete").exists()


def test_a_single_scope_never_prunes(both_ends):
    """One file knows nothing about what the other one carries."""
    _obsolete_action()

    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(failure=False, onisep_records=[])
        ImportFormationActions(scope="lycee")

    assert FormationAction.objects.filter(onisep_id="obsolete").exists()


def test_a_link_the_feed_still_carries_survives(both_ends, formation_action_record):
    action = _obsolete_action()
    still_listed = formation_action_record(
        onisep_id=action.onisep_id,
        formation_id=action.formation.onisep_id,
        school_id=action.school.onisep_id,
    )

    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(failure=False, onisep_records=[still_listed])
        ImportFormationActions()

    assert FormationAction.objects.filter(onisep_id="obsolete").exists()


def test_a_link_the_upsert_could_not_resolve_is_not_pruned(both_ends, formation_action_record):
    """The feed still describes it, even if this run could not resolve its établissement."""
    action = _obsolete_action()
    unresolvable = formation_action_record(
        onisep_id=action.onisep_id,
        formation_id=action.formation.onisep_id,
        school_id="inconnu",
    )

    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(failure=False, onisep_records=[unresolvable])
        ImportFormationActions()

    assert FormationAction.objects.filter(onisep_id="obsolete").exists()


def test_a_failed_download_carries_its_message_up(both_ends):
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Onisep injoignable"], status_code=None, network_error=True
        )
        result = ImportFormationActions(scope="lycee")

    assert result.failure
    assert result.errors == ["Onisep injoignable"]
    assert FormationAction.objects.count() == 0


def test_a_transient_download_failure_stays_transient_one_layer_up(both_ends):
    """The task decides whether to retry, and it only ever sees the import service."""
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Onisep indisponible"], status_code=503, network_error=False
        )
        result = ImportFormationActions(scope="lycee")

    assert result.failed_with_transient_error()


def test_a_permanent_download_failure_is_not_worth_retrying(both_ends):
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Introuvable"], status_code=404, network_error=False
        )
        result = ImportFormationActions(scope="lycee")

    assert not result.failed_with_transient_error()
