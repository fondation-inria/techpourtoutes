from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from techpourtoutes.models import FormationAction
from techpourtoutes.services.formation_action.import_formation_actions import (
    ImportFormationActions,
)

pytestmark = pytest.mark.django_db

SERVICE = (
    "techpourtoutes.management.commands.import_onisep_formation_actions.ImportFormationActions"
)


@pytest.fixture
def imported_ends(db):
    call_command("import_onisep_schools", sample=True)
    call_command("import_onisep_formations", sample=True)


def test_the_command_hands_its_arguments_to_the_service():
    with patch(SERVICE) as service:
        # The command reads SCOPES off the class to build its --scope choices.
        service.SCOPES = ImportFormationActions.SCOPES
        service.return_value.failure = False
        call_command("import_onisep_formation_actions", "--scope", "lycee", "--sample")

    service.assert_called_once_with(scope="lycee", sample=True)


def test_the_command_links_the_samples(imported_ends):
    call_command("import_onisep_formation_actions", sample=True)

    assert FormationAction.objects.count() == 200


def test_the_command_reports_the_rows_it_created(imported_ends, capsys):
    call_command("import_onisep_formation_actions", sample=True)

    assert "200 actions de formation créées" in capsys.readouterr().out


def test_if_empty_skips_the_import_when_rows_already_exist(imported_ends):
    call_command("import_onisep_formation_actions", sample=True)

    with patch(SERVICE) as service:
        call_command("import_onisep_formation_actions", if_empty=True)

    service.assert_not_called()


def test_a_failed_import_stops_the_command():
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["Onisep injoignable"]
        with pytest.raises(CommandError, match="Onisep injoignable"):
            call_command("import_onisep_formation_actions")


def test_a_failed_import_is_logged_so_sentry_sees_it(command_logs):
    """CommandError alone is invisible: Django turns it into sys.exit()."""
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["Onisep injoignable"]
        with pytest.raises(CommandError):
            call_command("import_onisep_formation_actions")

    assert "Onisep injoignable" in command_logs.text
