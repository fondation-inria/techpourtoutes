from celery import chain
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.tasks import (
    flag_recommended_schools_task,
    flag_training_ambassador_schools_task,
    import_carif_oref_formations_task,
    import_onisep_formation_actions_task,
    import_onisep_formations_task,
    import_onisep_schools_task,
)

# Order matters: the actions need both of their ends in place, the ambassadrice flag and the
# recommendation flag both need the schools and formations, and the Carif-Oref catalogue hangs onto
# the établissements Onisep has just given us.
# The remapping closes the merge for the databases that predate it.
STEPS = [
    "import_onisep_schools",
    "import_onisep_formations",
    "import_onisep_formation_actions",
    "flag_training_ambassador_schools",
    "flag_recommended_schools",
    "import_carif_oref_formations",
]
# Neither flagging step downloads anything, so neither has a --sample counterpart.
STEPS_WITHOUT_SAMPLE = ["flag_training_ambassador_schools", "flag_recommended_schools"]

# `--sample` means "stay offline", and this step has no committed sample to read instead.
ONLINE_ONLY_STEP = "import_carif_oref_formations"

# The ambassadrice list is the same curated file either way; the catalogue takes no sample.
STEPS_WITHOUT_A_SAMPLE = {"flag_training_ambassador_schools", ONLINE_ONLY_STEP}


class Command(BaseCommand):
    help = "Run every Onisep import in order, then remap the parcours left by the school merge"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sample",
            action="store_true",
            help="Importer les échantillons commités au lieu d'interroger Onisep.",
        )
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Ignorer l'import si la table contient déjà des lignes.",
        )
        parser.add_argument(
            # `async` is a Python keyword, so it cannot be the option's destination.
            "--async",
            dest="async_",
            action="store_true",
            help="Déléguer l'import au worker, qui rejouera les pannes passagères d'Onisep.",
        )

    def handle(self, *args, **options):
        if not options["async_"]:
            self._import_now(options)
            return
        if options["if_empty"]:
            raise CommandError("  --if-empty ne s'applique pas à l'import asynchrone.")
        self._enqueue(sample=options["sample"])

    def _import_now(self, options):
        for step in self._steps(sample=options["sample"]):
            self.stdout.write(f"{step}…")
            call_command(step, **self._options_for(step, options))
        self.stdout.write("remap_training_experience_schools…")
        call_command("remap_training_experience_schools")

    def _enqueue(self, *, sample):
        """A chain, not a group: every step needs the previous one, and retrying one step
        must not re-download the 110 MB the others already fetched."""
        tasks = [
            import_onisep_schools_task.si(sample=sample),
            import_onisep_formations_task.si(sample=sample),
            import_onisep_formation_actions_task.si(sample=sample),
            flag_training_ambassador_schools_task.si(),
            flag_recommended_schools_task.si(),
        ]
        if not sample:
            tasks.append(import_carif_oref_formations_task.si())
        chain(*tasks).delay()
        self.stdout.write(self.style.SUCCESS("  Import enfilé sur le worker."))

    def _steps(self, *, sample):
        """A sampled run stays offline, so it leaves out the step that cannot."""
        if not sample:
            return STEPS
        return [step for step in STEPS if step != ONLINE_ONLY_STEP]

    def _options_for(self, step, options):
        """Only the Onisep imports have a sample counterpart; the flagging steps work off
        whatever is already in the database either way."""
        step_options = {"if_empty": options["if_empty"]}
        if step not in STEPS_WITHOUT_SAMPLE:
            step_options["sample"] = options["sample"]
        return step_options
