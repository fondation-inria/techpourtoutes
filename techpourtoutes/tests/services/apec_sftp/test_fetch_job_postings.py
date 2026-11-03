from datetime import timedelta
from unittest.mock import MagicMock, patch

import paramiko
import pytest
from django.utils import timezone

from techpourtoutes.services.apec_sftp.fetch_job_postings import FetchApecJobPostings
from techpourtoutes.services.base import ErrorKind

DOWNLOAD = "techpourtoutes.services.apec_sftp.fetch_job_postings.ApecSftpClient.download_export"


def _export(*, days_ago=0):
    exported_at = timezone.localtime() - timedelta(days=days_ago)
    return f"""<?xml version='1.0' encoding='UTF-8'?>
<Export_offres>
  <Export>
    <Partenaire>TECHPOURTOUTES</Partenaire>
    <Date_export>{exported_at:%d/%m/%Y %H:%M:%S}</Date_export>
  </Export>
  <Offre_emploi>
    <Reference_apec>179254673W</Reference_apec>
  </Offre_emploi>
</Export_offres>
"""


def _serving(content):
    return lambda export: export.write(content.encode())


@pytest.mark.parametrize("days_ago", [0, 1, 3])
def test_the_export_is_downloaded_and_read(days_ago):
    """Apec writes no export on Sundays and Mondays: Saturday's is read again, unchanged."""
    with patch(DOWNLOAD, side_effect=_serving(_export(days_ago=days_ago))):
        result = FetchApecJobPostings()

    assert result.success
    assert result.apec_records == [{"Reference_apec": "179254673W"}]


def test_an_export_left_unchanged_for_more_than_three_days_fails_for_good():
    """Apec has stopped writing it: someone has to find out why."""
    with patch(DOWNLOAD, side_effect=_serving(_export(days_ago=4))):
        result = FetchApecJobPostings()

    assert result.failure
    assert result.error_kind is ErrorKind.PERMANENT


def test_an_export_declaring_entities_fails_for_good():
    """Apec declares none: a DTD would only be there to blow up or leak through the parser."""
    export = '<!DOCTYPE a [<!ENTITY x "y">]><Export_offres>&x;</Export_offres>'
    with patch(DOWNLOAD, side_effect=_serving(export)):
        result = FetchApecJobPostings()

    assert result.failure
    assert result.error_kind is ErrorKind.PERMANENT


def test_an_export_that_is_not_xml_fails_for_good():
    with patch(DOWNLOAD, side_effect=_serving("<Export_offres><Offre_emploi>")):
        result = FetchApecJobPostings()

    assert result.failure
    assert result.error_kind is ErrorKind.PERMANENT


@pytest.mark.parametrize(
    "error",
    [
        paramiko.AuthenticationException(),
        paramiko.BadHostKeyException("sftp.apec.fr", MagicMock(), MagicMock()),
        FileNotFoundError(),
    ],
    ids=["refused", "another host key", "missing"],
)
def test_refused_credentials_another_host_key_or_a_missing_export_fail_for_good(error):
    """A host key that changed is someone posing as Apec until Apec says otherwise."""
    with patch(DOWNLOAD, side_effect=error):
        result = FetchApecJobPostings()

    assert result.failure
    assert result.error_kind is ErrorKind.PERMANENT


@pytest.mark.parametrize(
    "error", [TimeoutError(), ConnectionRefusedError(), paramiko.SSHException()]
)
def test_a_server_out_of_reach_or_a_download_cut_short_is_worth_trying_again(error):
    with patch(DOWNLOAD, side_effect=error):
        result = FetchApecJobPostings()

    assert result.failure
    assert result.error_kind is ErrorKind.TRANSIENT
