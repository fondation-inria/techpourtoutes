from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from techpourtoutes.models import School
from techpourtoutes.services.school.import_schools import ImportSchools

pytestmark = pytest.mark.django_db

SERVICE = "techpourtoutes.management.commands.import_onisep_schools.ImportSchools"


def test_the_command_hands_its_arguments_to_the_service():
    with patch(SERVICE) as service:
        # The command reads SCOPES off the class to build its --scope choices.
        service.SCOPES = ImportSchools.SCOPES
        service.return_value.failure = False
        call_command("import_onisep_schools", "--scope", "secondary", "--sample")

    service.assert_called_once_with(scope="secondary", sample=True)


def test_the_command_imports_the_samples():
    call_command("import_onisep_schools", sample=True)

    assert School.objects.secondary().exists()
    assert School.objects.higher_ed().exists()


def test_the_command_reports_the_rows_it_created(capsys):
    call_command("import_onisep_schools", sample=True)

    assert f"{School.objects.count()} établissements créés" in capsys.readouterr().out


def test_if_empty_skips_the_import_when_rows_already_exist():
    School(onisep_id="1", name="Déjà là").save()

    with patch(SERVICE) as service:
        call_command("import_onisep_schools", if_empty=True)

    service.assert_not_called()
    assert School.objects.count() == 1


def test_if_empty_runs_the_import_on_an_empty_table():
    call_command("import_onisep_schools", sample=True, if_empty=True)

    assert School.objects.count() > 1


def test_if_empty_runs_the_import_when_only_merge_placeholders_are_there():
    """Migration 0036 leaves the table full of `legacy-` rows, so a plain `exists()` would
    skip the very first import — and the remapping would then find nothing to point at."""
    School(onisep_id="legacy-s-0", name="Lycée Voltaire", uai="0750001A").save()

    call_command("import_onisep_schools", sample=True, if_empty=True)

    assert School.objects.imported().count() > 1


def test_a_failed_import_stops_the_command():
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["Onisep injoignable"]
        with pytest.raises(CommandError, match="Onisep injoignable"):
            call_command("import_onisep_schools")


def test_a_failed_import_is_logged_so_sentry_sees_it(command_logs):
    """CommandError alone is invisible: Django turns it into sys.exit()."""
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["Onisep injoignable"]
        with pytest.raises(CommandError):
            call_command("import_onisep_schools")

    assert "Onisep injoignable" in command_logs.text
