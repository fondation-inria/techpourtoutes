import pytest
from django.core.management import call_command

from techpourtoutes.models import School
from techpourtoutes.tasks.flag_training_ambassador_schools import (
    flag_training_ambassador_schools_task,
)

# Eager mode is on for the whole suite (root conftest), so a task runs inline.
pytestmark = pytest.mark.django_db


def test_the_task_flags_the_curated_schools():
    call_command("import_onisep_schools", sample=True)

    flag_training_ambassador_schools_task()

    assert School.objects.training_ambassador().count() == 90
