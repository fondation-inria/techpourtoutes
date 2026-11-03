from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from techpourtoutes.models import JobPosting
from techpourtoutes.services.job_posting.upsert_apec_job_postings import UpsertApecJobPostings

pytestmark = pytest.mark.django_db

COMMAND = "techpourtoutes.management.commands.import_apec_job_postings"
SERVICE = f"{COMMAND}.ImportApecJobPostings"
TASK = f"{COMMAND}.import_apec_job_postings_task"


def test_the_command_calls_the_service():
    with patch(SERVICE) as service:
        service.return_value.failure = False
        call_command("import_apec_job_postings")

    service.assert_called_once_with(sample=False)


def test_sample_asks_the_service_for_the_committed_file():
    with patch(SERVICE) as service:
        service.return_value.failure = False
        call_command("import_apec_job_postings", sample=True)

    service.assert_called_once_with(sample=True)


def test_if_empty_skips_the_import_once_apec_offers_are_in(capsys, apec_record):
    UpsertApecJobPostings(records=[apec_record()])

    with patch(SERVICE) as service:
        call_command("import_apec_job_postings", if_empty=True)

    service.assert_not_called()
    assert "déjà" in capsys.readouterr().out


def test_if_empty_counts_the_unpublished_offers_in(apec_record):
    UpsertApecJobPostings(records=[apec_record()])
    JobPosting.objects.update(hidden=True)

    with patch(SERVICE) as service:
        call_command("import_apec_job_postings", if_empty=True)

    service.assert_not_called()


def test_if_empty_runs_the_import_when_only_other_sources_are_in():
    JobPosting(
        source=JobPosting.Source.MYFUTURE,
        external_id="22NisRqehckrMvEu3",
        title="Stage en électricité générale",
        company_name="Didier Ducom",
        description="…",
        city="Caupenne-d'Armagnac",
        domains=["électrotechnique"],
        category=JobPosting.Category.TROISIEME_INTERNSHIP,
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        url="https://myfutu.re/internships/offers/22NisRqehckrMvEu3",
    ).save()

    with patch(SERVICE) as service:
        service.return_value.failure = False
        call_command("import_apec_job_postings", if_empty=True)

    service.assert_called_once_with(sample=False)


def test_the_command_reports_how_many_offers_are_in(capsys, apec_record):
    with patch(
        "techpourtoutes.services.job_posting.import_apec_job_postings.FetchApecJobPostings"
    ) as fetch:
        fetch.return_value.failure = False
        fetch.return_value.apec_records = [apec_record("a"), apec_record("b")]
        call_command("import_apec_job_postings")

    assert "2 offres Apec" in capsys.readouterr().out


@override_settings(SCHEDULED_IMPORTS_ENABLED=True)
def test_async_hands_the_import_to_the_worker():
    with patch(SERVICE) as service, patch(TASK) as task:
        call_command("import_apec_job_postings", async_=True)

    task.delay.assert_called_once_with()
    service.assert_not_called()


@override_settings(SCHEDULED_IMPORTS_ENABLED=False)
def test_async_does_nothing_where_the_scheduled_import_is_disabled(capsys):
    """The cron runs on every app — staging and review apps included — but production."""
    with patch(SERVICE) as service, patch(TASK) as task:
        call_command("import_apec_job_postings", async_=True)

    task.delay.assert_not_called()
    service.assert_not_called()
    assert "désactivé" in capsys.readouterr().out


@pytest.mark.parametrize("option", ["sample", "if_empty"])
def test_async_rejects_the_options_of_an_immediate_import(option):
    with patch(TASK) as task, pytest.raises(CommandError):
        call_command("import_apec_job_postings", async_=True, **{option: True})

    task.delay.assert_not_called()


def test_a_failed_import_stops_the_command():
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["Apec injoignable"]
        with pytest.raises(CommandError, match="Apec injoignable"):
            call_command("import_apec_job_postings")


def test_a_failed_import_is_logged_so_sentry_sees_it(command_logs):
    """CommandError alone is invisible: Django turns it into sys.exit()."""
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["Apec injoignable"]
        with pytest.raises(CommandError):
            call_command("import_apec_job_postings")

    assert "Apec injoignable" in command_logs.text
