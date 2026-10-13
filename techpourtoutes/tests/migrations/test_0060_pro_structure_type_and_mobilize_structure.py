import importlib

import pytest
from django.apps import apps

from techpourtoutes.models import Pro

migration = importlib.import_module(
    "techpourtoutes.migrations.0060_pro_structure_type_and_mobilize_structure"
)

pytestmark = pytest.mark.django_db


def _pro(email, situation, structure_type=""):
    pro = Pro(
        username=email,
        email=email,
        first_name="Hedy",
        last_name="Lamarr",
        professional_situation=situation,
        structure_type=structure_type,
    )
    pro.save()
    return pro


def test_the_structure_type_of_a_pro_with_no_structure_follows_her_situation():
    retired = _pro("retired@example.com", "retired")
    jobless = _pro("jobless@example.com", "jobless")

    migration.infer_structure_type(apps, None)

    retired.refresh_from_db()
    jobless.refresh_from_db()
    assert (retired.structure_type, jobless.structure_type) == ("retired", "jobless")


def test_the_structure_type_of_a_working_pro_stays_unknown():
    working = _pro("working@example.com", "working")

    migration.infer_structure_type(apps, None)

    working.refresh_from_db()
    assert working.structure_type == ""
