import pytest

from techpourtoutes.models import Formation, FormationAction, School
from techpourtoutes.tasks.flag_recommended_schools import flag_recommended_schools_task

# Eager mode is on for the whole suite (root conftest), so a task runs inline.
pytestmark = pytest.mark.django_db


def test_the_task_flags_the_recommended_schools():
    school = School(onisep_id="1", name="Lycée pro CIEL", status="public")
    school.save()
    formation = Formation(onisep_id="f1", name="Bac CIEL", acronym="CIEL")
    formation.save()
    FormationAction(formation=formation, school=school).save()

    flag_recommended_schools_task()

    assert School.objects.get(onisep_id="1").recommended
