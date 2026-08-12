from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from techpourtoutes.models import Formation

pytestmark = pytest.mark.django_db

SERVICE = "techpourtoutes.management.commands.import_onisep_formations.ImportFormations"


def test_the_command_hands_its_arguments_to_the_service():
    with patch(SERVICE) as service:
        service.return_value.failure = False
        call_command("import_onisep_formations", "--sample")

    service.assert_called_once_with(sample=True)


def test_the_command_imports_the_sample():
    call_command("import_onisep_formations", sample=True)

    assert Formation.objects.count() == 149


def test_the_command_reports_the_rows_it_created(capsys):
    call_command("import_onisep_formations", sample=True)

    assert "149 formations créées" in capsys.readouterr().out


def test_if_empty_skips_the_import_when_rows_already_exist():
    Formation(onisep_id="1", name="Déjà là").save()

    with patch(SERVICE) as service:
        call_command("import_onisep_formations", if_empty=True)

    service.assert_not_called()
    assert Formation.objects.count() == 1


def test_a_failed_import_stops_the_command():
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["Onisep injoignable"]
        with pytest.raises(CommandError, match="Onisep injoignable"):
            call_command("import_onisep_formations")


def test_a_failed_import_is_logged_so_sentry_sees_it(command_logs):
    """CommandError alone is invisible: Django turns it into sys.exit()."""
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["Onisep injoignable"]
        with pytest.raises(CommandError):
            call_command("import_onisep_formations")

    assert "Onisep injoignable" in command_logs.text
