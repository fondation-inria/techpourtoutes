from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.models import School
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.school.import_schools import ImportSchools

pytestmark = pytest.mark.django_db

FETCH = "techpourtoutes.services.school.import_schools.FetchOnisepSchools"


def test_the_samples_are_read_without_touching_the_network():
    with patch(FETCH) as fetch:
        result = ImportSchools(sample=True)

    fetch.assert_not_called()
    assert result.success
    assert School.objects.secondary().exists()
    assert School.objects.higher_ed().exists()


def test_every_scope_is_covered_by_default():
    ImportSchools(sample=True)

    assert School.objects.filter(secondary=True, higher_ed=True).count() == 5


def test_a_single_scope_leaves_the_other_alone():
    ImportSchools(scope="secondary", sample=True)

    assert School.objects.secondary().exists()
    assert not School.objects.higher_ed().exists()


def test_without_a_sample_each_scope_is_downloaded(school_record):
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(failure=False, onisep_records=[school_record()])
        ImportSchools()

    assert [call.kwargs["scope"] for call in fetch.call_args_list] == ["secondary", "higher_ed"]
    assert School.objects.get(onisep_id="14008").higher_ed


def test_a_failed_download_carries_its_message_up():
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Onisep injoignable"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportSchools(scope="higher_ed")

    assert result.failure
    assert result.errors == ["Onisep injoignable"]
    assert School.objects.count() == 0


def test_a_transient_download_failure_stays_transient_one_layer_up():
    """The task decides whether to retry, and it only ever sees the import service."""
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Onisep indisponible"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportSchools(scope="higher_ed")

    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_permanent_download_failure_is_not_worth_retrying():
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True,
            errors=["Jeu de données introuvable"],
            error_kind=ErrorKind.PERMANENT,
        )
        result = ImportSchools(scope="higher_ed")

    assert result.error_kind is ErrorKind.PERMANENT
