from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.models import Formation
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.formation.import_formations import ImportFormations

pytestmark = pytest.mark.django_db

FETCH = "techpourtoutes.services.formation.import_formations.FetchOnisepFormations"


def test_the_sample_is_read_without_touching_the_network():
    with patch(FETCH) as fetch:
        result = ImportFormations(sample=True)

    fetch.assert_not_called()
    assert result.success
    assert Formation.objects.count() == 149


def test_without_a_sample_the_dataset_is_downloaded(formation_record):
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(failure=False, onisep_records=[formation_record()])
        ImportFormations()

    fetch.assert_called_once_with()
    assert Formation.objects.get(onisep_id="9701")


def test_a_failed_download_carries_its_message_up():
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Onisep injoignable"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportFormations()

    assert result.failure
    assert result.errors == ["Onisep injoignable"]
    assert Formation.objects.count() == 0


def test_a_transient_download_failure_stays_transient_one_layer_up():
    """The task decides whether to retry, and it only ever sees the import service."""
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Onisep indisponible"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportFormations()

    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_permanent_download_failure_is_not_worth_retrying():
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Introuvable"], error_kind=ErrorKind.PERMANENT
        )
        result = ImportFormations()

    assert result.error_kind is ErrorKind.PERMANENT
