from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.models import JobPosting
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.job_posting.import_myfuture_job_postings import (
    ImportMyFutureJobPostings,
)

pytestmark = pytest.mark.django_db

FETCH = "techpourtoutes.services.job_posting.import_myfuture_job_postings.FetchMyFutureJobPostings"
UPSERT = (
    "techpourtoutes.services.job_posting.import_myfuture_job_postings.UpsertMyFutureJobPostings"
)


def _serving(httpx_mock, *records):
    """`/offers` lists them, `/internships` nothing more."""
    httpx_mock.add_response(json=list(records))
    httpx_mock.add_response(json=[])


def test_the_offers_are_downloaded_and_upserted(httpx_mock, myfuture_record):
    _serving(httpx_mock, myfuture_record())

    result = ImportMyFutureJobPostings()

    assert result.success
    assert JobPosting.objects.get(external_id="22NisRqehckrMvEu3")


def test_the_offers_reach_the_upsert_one_at_a_time(httpx_mock, myfuture_record):
    """Every page is written to disk as it comes: they are never all held in memory."""
    _serving(httpx_mock, myfuture_record())

    with patch(UPSERT) as upsert:
        ImportMyFutureJobPostings()

    assert isinstance(upsert.call_args.kwargs["records"], Iterator)


def test_a_sample_reads_the_committed_file_instead_of_the_api():
    with patch(FETCH) as fetch:
        result = ImportMyFutureJobPostings(sample=True)

    fetch.assert_not_called()
    assert result.success
    assert set(JobPosting.objects.values_list("category", flat=True)) == {
        JobPosting.Category.TROISIEME_INTERNSHIP,
        JobPosting.Category.HIGHER_ED_INTERNSHIP,
        JobPosting.Category.APPRENTICESHIP,
        JobPosting.Category.FIRST_JOB,
        JobPosting.Category.PFMP,
    }


def test_a_failed_fetch_deletes_nothing(httpx_mock, myfuture_record):
    """Half the offers missing would otherwise read as half the offers withdrawn."""
    _serving(httpx_mock, myfuture_record())
    ImportMyFutureJobPostings()
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["MyFuture injoignable"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportMyFutureJobPostings()

    assert result.failure
    assert result.errors == ["MyFuture injoignable"]
    assert JobPosting.objects.count() == 1


def test_a_transient_fetch_failure_stays_transient_one_layer_up():
    """The task decides whether to retry, and it only ever sees the import service."""
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["MyFuture indisponible"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportMyFutureJobPostings()

    assert result.error_kind is ErrorKind.TRANSIENT
