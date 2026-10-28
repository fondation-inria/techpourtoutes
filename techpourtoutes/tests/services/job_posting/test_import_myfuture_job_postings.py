from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.models import JobPosting
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.job_posting.import_myfuture_job_postings import (
    ImportMyFutureJobPostings,
)

pytestmark = pytest.mark.django_db

FETCH = "techpourtoutes.services.job_posting.import_myfuture_job_postings.FetchMyFutureJobPostings"


def test_the_offers_are_downloaded_and_upserted(myfuture_record):
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(failure=False, myfuture_records=[myfuture_record()])
        result = ImportMyFutureJobPostings()

    fetch.assert_called_once_with()
    assert result.success
    assert JobPosting.objects.get(external_id="22NisRqehckrMvEu3")


def test_a_failed_fetch_deletes_nothing(myfuture_record):
    """Half the offers missing would otherwise read as half the offers withdrawn."""
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(failure=False, myfuture_records=[myfuture_record()])
        ImportMyFutureJobPostings()
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
