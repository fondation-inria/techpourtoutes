from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.models import Formation, School
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.formation.import_carif_oref_formations import (
    ImportCarifOrefFormations,
)

pytestmark = pytest.mark.django_db

FETCH = "techpourtoutes.services.formation.import_carif_oref_formations.FetchCarifOrefFormations"


@pytest.fixture
def cfa(db):
    school = School(onisep_id="1967", name="CFAI Alsace", siret="38855948600070", uai="0681832X")
    school.save()
    return school


def test_the_catalogue_is_downloaded_and_upserted(cfa, carif_oref_record):
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(failure=False, carif_oref_records=[carif_oref_record()])
        result = ImportCarifOrefFormations()

    fetch.assert_called_once_with()
    assert result.success
    assert Formation.objects.get(onisep_id="5978")


def test_a_failed_fetch_carries_its_message_up():
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Carif-Oref injoignable"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportCarifOrefFormations()

    assert result.failure
    assert result.errors == ["Carif-Oref injoignable"]
    assert Formation.objects.count() == 0


def test_a_transient_fetch_failure_stays_transient_one_layer_up():
    """The task decides whether to retry, and it only ever sees the import service."""
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Carif-Oref indisponible"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportCarifOrefFormations()

    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_permanent_fetch_failure_is_not_worth_retrying():
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Introuvable"], error_kind=ErrorKind.PERMANENT
        )
        result = ImportCarifOrefFormations()

    assert result.error_kind is ErrorKind.PERMANENT
