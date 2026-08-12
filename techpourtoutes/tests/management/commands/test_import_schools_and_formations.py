from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from techpourtoutes.models import Formation, FormationAction, School

pytestmark = pytest.mark.django_db

CHAIN = "techpourtoutes.management.commands.import_schools_and_formations.chain"


def test_the_master_command_imports_everything_in_order():
    call_command("import_schools_and_formations", sample=True)

    assert School.objects.count() == 188
    assert Formation.objects.count() == 149
    # The actions need both ends imported first: a wrong order would leave this at zero.
    assert FormationAction.objects.count() == 200
    assert School.objects.training_ambassador().count() == 90


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
    ]
    assert School.objects.count() == 0


def test_async_runs_the_same_import_when_celery_is_eager():
    """Eager mode is on for the whole suite, so the chain unrolls inline."""
    call_command("import_schools_and_formations", async_=True, sample=True)

    assert School.objects.count() == 188
    assert Formation.objects.count() == 149
    assert FormationAction.objects.count() == 200
    assert School.objects.training_ambassador().count() == 90


def test_async_refuses_if_empty():
    """Nobody carries the guard once the sub-commands are bypassed, so we say so."""
    with pytest.raises(CommandError, match="--if-empty"):
        call_command("import_schools_and_formations", async_=True, if_empty=True)
