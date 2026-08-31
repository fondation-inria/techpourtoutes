from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from techpourtoutes.models import Formation, FormationAction, School

pytestmark = pytest.mark.django_db

SERVICE = (
    "techpourtoutes.management.commands.import_carif_oref_formations.ImportCarifOrefFormations"
)


def _link_without_an_onisep_id():
    formation = Formation(onisep_id="5978", name="BTS")
    formation.save()
    school = School(onisep_id="1967", name="CFAI Alsace")
    school.save()
    FormationAction(onisep_id=None, formation=formation, school=school).save()


def test_the_command_calls_the_service():
    with patch(SERVICE) as service:
        service.return_value.failure = False
        call_command("import_carif_oref_formations")

    service.assert_called_once_with()


def test_the_command_reports_the_rows_it_created(capsys, carif_oref_record):
    School(onisep_id="1967", name="CFAI", siret="38855948600070", uai="0681832X").save()
    with patch(
        "techpourtoutes.services.formation.import_carif_oref_formations.FetchCarifOrefFormations"
    ) as fetch:
        fetch.return_value.failure = False
        fetch.return_value.carif_oref_records = [carif_oref_record()]
        call_command("import_carif_oref_formations")

    output = capsys.readouterr().out
    assert "1 formation" in output
    assert "1 lien" in output


def test_if_empty_skips_the_import_once_the_catalogue_is_in():
    _link_without_an_onisep_id()

    with patch(SERVICE) as service:
        call_command("import_carif_oref_formations", if_empty=True)

    service.assert_not_called()


def test_if_empty_runs_the_import_when_only_onisep_links_are_there(school, formation):
    """The Onisep steps run first and always fill the tables: their links are not ours."""
    with patch(SERVICE) as service:
        service.return_value.failure = False
        call_command("import_carif_oref_formations", if_empty=True)

    service.assert_called_once_with()


def test_a_failed_import_stops_the_command():
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["Carif-Oref injoignable"]
        with pytest.raises(CommandError, match="Carif-Oref injoignable"):
            call_command("import_carif_oref_formations")


def test_a_failed_import_is_logged_so_sentry_sees_it(command_logs):
    """CommandError alone is invisible: Django turns it into sys.exit()."""
    with patch(SERVICE) as service:
        service.return_value.failure = True
        service.return_value.errors = ["Carif-Oref injoignable"]
        with pytest.raises(CommandError):
            call_command("import_carif_oref_formations")

    assert "Carif-Oref injoignable" in command_logs.text
