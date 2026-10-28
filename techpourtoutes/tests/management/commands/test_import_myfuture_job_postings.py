from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

pytestmark = pytest.mark.django_db

COMMAND = "techpourtoutes.management.commands.import_myfuture_job_postings"
SERVICE = f"{COMMAND}.ImportMyFutureJobPostings"
TASK = f"{COMMAND}.import_myfuture_job_postings_task"


def test_the_command_calls_the_service():
    with patch(SERVICE) as service:
        service.return_value.failure = False
        call_command("import_myfuture_job_postings")

    service.assert_called_once_with()


def test_the_command_reports_how_many_offers_are_in(capsys, myfuture_record):
    with patch(
        "techpourtoutes.services.job_posting.import_myfuture_job_postings.FetchMyFutureJobPostings"
    ) as fetch:
        fetch.return_value.failure = False
        fetch.return_value.myfuture_records = [myfuture_record("a"), myfuture_record("b")]
        call_command("import_myfuture_job_postings")

    assert "2 offres MyFuture" in capsys.readouterr().out


def test_async_hands_the_import_to_the_worker():
    with patch(SERVICE) as service, patch(TASK) as task:
        call_command("import_myfuture_job_postings", async_=True)

    task.delay.assert_called_once_with()
    service.assert_not_called()


def test_a_failed_import_stops_the_command():
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["MyFuture injoignable"]
        with pytest.raises(CommandError, match="MyFuture injoignable"):
            call_command("import_myfuture_job_postings")


def test_a_failed_import_is_logged_so_sentry_sees_it(command_logs):
    """CommandError alone is invisible: Django turns it into sys.exit()."""
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["MyFuture injoignable"]
        with pytest.raises(CommandError):
            call_command("import_myfuture_job_postings")

    assert "MyFuture injoignable" in command_logs.text
