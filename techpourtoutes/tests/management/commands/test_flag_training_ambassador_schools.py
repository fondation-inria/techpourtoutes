from unittest.mock import patch

import pytest
from django.core.management import call_command

from techpourtoutes.models import School

pytestmark = pytest.mark.django_db

SERVICE = (
    "techpourtoutes.management.commands.flag_training_ambassador_schools."
    "FlagTrainingAmbassadorSchools"
)


def test_flag_marks_the_schools_listed_in_the_committed_file():
    call_command("import_onisep_schools", sample=True)

    call_command("flag_training_ambassador_schools")

    assert School.objects.training_ambassador().count() == 90


def test_flag_survives_a_later_school_import():
    call_command("import_onisep_schools", sample=True)
    call_command("flag_training_ambassador_schools")

    call_command("import_onisep_schools", sample=True)

    assert School.objects.training_ambassador().count() == 90


def test_if_empty_skips_when_schools_are_already_flagged():
    call_command("import_onisep_schools", sample=True)
    call_command("flag_training_ambassador_schools")

    with patch(SERVICE) as service:
        call_command("flag_training_ambassador_schools", if_empty=True)

    service.assert_not_called()
