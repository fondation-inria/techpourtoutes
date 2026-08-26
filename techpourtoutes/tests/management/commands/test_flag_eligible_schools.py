from unittest.mock import patch

import pytest
from django.core.management import call_command

from techpourtoutes.models import Formation, FormationAction, School

pytestmark = pytest.mark.django_db

SERVICE = "techpourtoutes.management.commands.flag_eligible_schools.FlagEligibleSchools"


def test_flag_marks_the_eligible_schools():
    school = School(onisep_id="1", name="Lycée pro CIEL", status="public")
    school.save()
    formation = Formation(onisep_id="f1", name="Bac CIEL", acronym="CIEL")
    formation.save()
    FormationAction(formation=formation, school=school).save()

    call_command("flag_eligible_schools")

    assert School.objects.get(onisep_id="1").eligible


def test_a_school_matching_no_criterion_loses_a_stale_flag():
    school = School(onisep_id="2", name="Lycée sans lien", status="public", eligible=True)
    school.save()

    call_command("flag_eligible_schools")

    assert not School.objects.get(onisep_id="2").eligible


def test_if_empty_skips_when_schools_are_already_flagged():
    School(onisep_id="3", name="Déjà éligible", status="public", eligible=True).save()

    with patch(SERVICE) as service:
        call_command("flag_eligible_schools", if_empty=True)

    service.assert_not_called()


def test_if_empty_runs_when_no_school_is_flagged_yet():
    School(onisep_id="4", name="Pas encore éligible", status="public").save()

    with patch(SERVICE) as service:
        call_command("flag_eligible_schools", if_empty=True)

    service.assert_called_once()
