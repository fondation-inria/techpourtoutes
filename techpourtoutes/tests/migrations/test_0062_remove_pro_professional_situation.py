import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from techpourtoutes.models import Pro

BEFORE = [("techpourtoutes", "0061_delete_new_pro_features_switch")]
AFTER = [("techpourtoutes", "0062_remove_pro_professional_situation")]


@pytest.fixture
def historical_apps(transactional_db):
    """The models as they stood when a pro still carried a professional situation."""
    executor = MigrationExecutor(connection)
    executor.migrate(BEFORE)
    yield executor.loader.project_state(BEFORE).apps
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def _migrate_to_after():
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(AFTER)


@pytest.fixture
def historical_pro(historical_apps):
    return historical_apps.get_model("techpourtoutes", "Pro")


def _pro(model, email, situation, structure_type=""):
    return model.objects.create(
        username=email,
        email=email,
        first_name="Hedy",
        last_name="Lamarr",
        professional_situation=situation,
        structure_type=structure_type,
    )


def test_a_retired_or_jobless_situation_becomes_her_structure_type(historical_pro):
    _pro(historical_pro, "retired@example.com", "retired")
    _pro(historical_pro, "jobless@example.com", "jobless")

    _migrate_to_after()

    assert Pro.objects.get(email="retired@example.com").structure_type == "retired"
    assert Pro.objects.get(email="jobless@example.com").structure_type == "jobless"


def test_a_structure_type_already_given_is_kept(historical_pro):
    _pro(historical_pro, "working@example.com", "working")
    _pro(historical_pro, "company@example.com", "retired", structure_type="company")

    _migrate_to_after()

    assert Pro.objects.get(email="working@example.com").structure_type == ""
    assert Pro.objects.get(email="company@example.com").structure_type == "company"


def test_a_student_takes_the_school_of_her_parcours_for_her_structure(
    historical_apps, historical_pro
):
    School = historical_apps.get_model("techpourtoutes", "School")
    TrainingExperience = historical_apps.get_model("techpourtoutes", "TrainingExperience")
    student = _pro(historical_pro, "student@example.com", "student")
    school = School.objects.create(onisep_id="490", name="Université Paris-Saclay")
    TrainingExperience.objects.create(
        user_id=student.pk,
        school=school,
        out_of_scope_formation_name="Licence informatique",
        start_date="2025-09-01",
        end_date="2026-08-31",
    )

    _migrate_to_after()

    pro = Pro.objects.get(email="student@example.com")
    assert (pro.structure_type, pro.structure_name) == ("higher_ed", "Université Paris-Saclay")


def test_a_student_without_a_parcours_still_studies_in_higher_education(historical_pro):
    _pro(historical_pro, "student@example.com", "student")

    _migrate_to_after()

    pro = Pro.objects.get(email="student@example.com")
    assert (pro.structure_type, pro.structure_name) == ("higher_ed", "")
