from unittest.mock import patch

import pytest
from django.core.management import call_command

from techpourtoutes.models import Formation, FormationAction, School

pytestmark = pytest.mark.django_db

SERVICE = "techpourtoutes.management.commands.flag_recommended_schools.FlagRecommendedSchools"


def test_flag_marks_the_recommended_schools():
    school = School(onisep_id="1", name="Lycée pro CIEL", status="public")
    school.save()
    formation = Formation(onisep_id="f1", name="Bac CIEL", acronym="CIEL")
    formation.save()
    FormationAction(formation=formation, school=school).save()

    call_command("flag_recommended_schools")

    assert School.objects.get(onisep_id="1").recommended


def test_a_school_matching_no_criterion_loses_a_stale_flag():
    school = School(onisep_id="2", name="Lycée sans lien", status="public", recommended=True)
    school.save()

    call_command("flag_recommended_schools")

    assert not School.objects.get(onisep_id="2").recommended


def test_if_empty_skips_when_schools_are_already_flagged():
    School(onisep_id="3", name="Déjà recommandée", status="public", recommended=True).save()

    with patch(SERVICE) as service:
        call_command("flag_recommended_schools", if_empty=True)

    service.assert_not_called()


def test_if_empty_runs_when_no_school_is_flagged_yet():
    School(onisep_id="4", name="Pas encore recommandée", status="public").save()

    with patch(SERVICE) as service:
        call_command("flag_recommended_schools", if_empty=True)

    service.assert_called_once()
