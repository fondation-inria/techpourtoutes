from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.models import JobPosting
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.job_posting.import_apec_job_postings import ImportApecJobPostings

pytestmark = pytest.mark.django_db

FETCH = "techpourtoutes.services.job_posting.import_apec_job_postings.FetchApecJobPostings"


def _fetched(records):
    return MagicMock(failure=False, apec_records=records)


def test_the_offers_are_downloaded_and_upserted(apec_record):
    with patch(FETCH) as fetch:
        fetch.return_value = _fetched([apec_record()])
        result = ImportApecJobPostings()

    assert result.success
    assert JobPosting.objects.get(external_id="179254673W")


def test_a_sample_reads_the_committed_file_instead_of_the_server():
    with patch(FETCH) as fetch:
        result = ImportApecJobPostings(sample=True)

    fetch.assert_not_called()
    assert result.success
    assert JobPosting.objects.filter(source=JobPosting.Source.APEC).exists()


def test_a_failed_fetch_deletes_nothing(apec_record):
    """An export that could not be read would otherwise read as every offer withdrawn."""
    with patch(FETCH) as fetch:
        fetch.return_value = _fetched([apec_record()])
        ImportApecJobPostings()
        fetch.return_value = MagicMock(
            failure=True, errors=["Apec injoignable"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportApecJobPostings()

    assert result.failure
    assert result.errors == ["Apec injoignable"]
    assert JobPosting.objects.count() == 1


def test_a_transient_fetch_failure_stays_transient_one_layer_up():
    """The task decides whether to retry, and it only ever sees the import service."""
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Apec indisponible"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportApecJobPostings()

    assert result.error_kind is ErrorKind.TRANSIENT


def test_an_export_without_any_offer_to_keep_fails_the_import():
    with patch(FETCH) as fetch:
        fetch.return_value = _fetched([])
        result = ImportApecJobPostings()

    assert result.failure
