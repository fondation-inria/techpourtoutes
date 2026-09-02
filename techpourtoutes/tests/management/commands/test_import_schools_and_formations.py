from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from techpourtoutes.models import Formation, FormationAction, School

pytestmark = pytest.mark.django_db

CHAIN = "techpourtoutes.management.commands.import_schools_and_formations.chain"
STEP_RUNNER = "techpourtoutes.management.commands.import_schools_and_formations.call_command"


def test_the_master_command_imports_everything_in_order():
    call_command("import_schools_and_formations", sample=True)

    assert School.objects.count() == 188
    assert Formation.objects.count() == 149
    # The actions need both ends imported first: a wrong order would leave this at zero.
    assert FormationAction.objects.count() == 200
    assert School.objects.training_ambassador().count() == 90
    assert School.objects.filter(recommended=True).count() == 107


def test_running_twice_changes_no_count():
    call_command("import_schools_and_formations", sample=True)
    counts = (School.objects.count(), Formation.objects.count(), FormationAction.objects.count())

    call_command("import_schools_and_formations", sample=True)

    assert (
        School.objects.count(),
        Formation.objects.count(),
        FormationAction.objects.count(),
    ) == counts
    assert School.objects.training_ambassador().count() == 90
    assert School.objects.filter(recommended=True).count() == 107


def test_if_empty_is_forwarded_to_every_step():
    call_command("import_schools_and_formations", sample=True)
    School.objects.all().update(name="marqueur")

    call_command("import_schools_and_formations", sample=True, if_empty=True)

    assert School.objects.exclude(name="marqueur").count() == 0


def test_async_hands_the_whole_chain_to_the_worker():
    with patch(CHAIN) as celery_chain:
        call_command("import_schools_and_formations", async_=True)

    assert celery_chain.call_count == 1
    steps = [signature.task for signature in celery_chain.call_args.args]
    assert steps == [
        "techpourtoutes.tasks.import_onisep_schools.import_onisep_schools_task",
        "techpourtoutes.tasks.import_onisep_formations.import_onisep_formations_task",
        "techpourtoutes.tasks.import_onisep_formation_actions."
        "import_onisep_formation_actions_task",
        "techpourtoutes.tasks.flag_training_ambassador_schools."
        "flag_training_ambassador_schools_task",
        "techpourtoutes.tasks.flag_recommended_schools.flag_recommended_schools_task",
        "techpourtoutes.tasks.import_carif_oref_formations.import_carif_oref_formations_task",
    ]
    assert School.objects.count() == 0


def test_async_runs_the_same_import_when_celery_is_eager():
    """Eager mode is on for the whole suite, so the chain unrolls inline."""
    call_command("import_schools_and_formations", async_=True, sample=True)

    assert School.objects.count() == 188
    assert Formation.objects.count() == 149
    assert FormationAction.objects.count() == 200
    assert School.objects.training_ambassador().count() == 90
    assert School.objects.filter(recommended=True).count() == 107


def test_the_carif_oref_step_closes_a_real_import():
    with patch(STEP_RUNNER) as run_step:
        call_command("import_schools_and_formations")

    assert [call.args[0] for call in run_step.call_args_list] == [
        "import_onisep_schools",
        "import_onisep_formations",
        "import_onisep_formation_actions",
        "flag_training_ambassador_schools",
        "import_carif_oref_formations",
        "remap_training_experience_schools",
    ]


def test_the_carif_oref_step_is_dropped_when_the_samples_are_asked_for():
    """`--sample` means "stay offline", and the catalogue has no committed sample."""
    with patch(STEP_RUNNER) as run_step:
        call_command("import_schools_and_formations", sample=True)

    assert "import_carif_oref_formations" not in [call.args[0] for call in run_step.call_args_list]


def test_the_carif_oref_step_is_never_handed_a_sample_flag():
    with patch(STEP_RUNNER) as run_step:
        call_command("import_schools_and_formations")

    options = next(
        call.kwargs
        for call in run_step.call_args_list
        if call.args[0] == "import_carif_oref_formations"
    )
    assert "sample" not in options


def test_the_carif_oref_task_is_left_out_of_a_sampled_chain():
    with patch(CHAIN) as celery_chain:
        call_command("import_schools_and_formations", async_=True, sample=True)

    steps = [signature.task for signature in celery_chain.call_args.args]
    assert not [step for step in steps if "carif_oref" in step]


def test_async_refuses_if_empty():
    """Nobody carries the guard once the sub-commands are bypassed, so we say so."""
    with pytest.raises(CommandError, match="--if-empty"):
        call_command("import_schools_and_formations", async_=True, if_empty=True)
