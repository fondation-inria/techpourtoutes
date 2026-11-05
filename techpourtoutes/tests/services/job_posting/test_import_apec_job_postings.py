from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.models import JobPosting
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.job_posting.import_apec_job_postings import ImportApecJobPostings

pytestmark = pytest.mark.django_db

FETCH = "techpourtoutes.services.job_posting.import_apec_job_postings.FetchApecJobPostings"
UPSERT = "techpourtoutes.services.job_posting.import_apec_job_postings.UpsertApecJobPostings"
DOWNLOAD = "techpourtoutes.services.apec_sftp.fetch_job_postings.ApecSftpClient.download_export"


def _serving(export):
    return patch(DOWNLOAD, side_effect=lambda file: file.write(export))


def test_the_offers_are_downloaded_and_upserted(apec_record, apec_export):
    with _serving(apec_export(apec_record())):
        result = ImportApecJobPostings()

    assert result.success
    assert JobPosting.objects.get(external_id="179254673W")


def test_the_offers_reach_the_upsert_one_at_a_time(apec_record, apec_export):
    """The export weighs some 60 MB: it is never held whole in memory."""
    with _serving(apec_export(apec_record())), patch(UPSERT) as upsert:
        upsert.return_value.failure = False
        ImportApecJobPostings()

    records = upsert.call_args.kwargs["records"]
    assert isinstance(records, Iterator)


def test_a_sample_reads_the_committed_file_instead_of_the_server():
    with patch(DOWNLOAD) as download:
        result = ImportApecJobPostings(sample=True)

    download.assert_not_called()
    assert result.success
    assert JobPosting.objects.filter(source=JobPosting.Source.APEC).exists()


def test_a_failed_fetch_deletes_nothing(apec_record, apec_export):
    """An export that could not be read would otherwise read as every offer withdrawn."""
    with _serving(apec_export(apec_record())):
        ImportApecJobPostings()
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Apec injoignable"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportApecJobPostings()

    assert result.failure
    assert result.errors == ["Apec injoignable"]
    assert JobPosting.objects.count() == 1


def test_an_export_cut_short_deletes_nothing(apec_record, apec_export):
    with _serving(apec_export(apec_record("kept"), apec_record("gone"))):
        ImportApecJobPostings()
    with _serving(apec_export(apec_record("kept"), apec_record("gone"))[:-40]):
        result = ImportApecJobPostings()

    assert result.failure
    assert JobPosting.objects.count() == 2


def test_a_transient_fetch_failure_stays_transient_one_layer_up():
    """The task decides whether to retry, and it only ever sees the import service."""
    with patch(FETCH) as fetch:
        fetch.return_value = MagicMock(
            failure=True, errors=["Apec indisponible"], error_kind=ErrorKind.TRANSIENT
        )
        result = ImportApecJobPostings()

    assert result.error_kind is ErrorKind.TRANSIENT


def test_an_export_without_any_offer_to_keep_fails_the_import(apec_export):
    with _serving(apec_export()):
        result = ImportApecJobPostings()

    assert result.failure
