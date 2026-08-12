from celery import chain
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.tasks import (
    flag_training_ambassador_schools_task,
    import_onisep_formation_actions_task,
    import_onisep_formations_task,
    import_onisep_schools_task,
)

# Order matters: the actions need both of their ends in place, and the ambassadrice flag needs
# the schools. The remapping closes the merge for the databases that predate it, and the
# formation linking needs the catalogue the steps above have just refreshed.
STEPS = [
    "import_onisep_schools",
    "import_onisep_formations",
    "import_onisep_formation_actions",
    "flag_training_ambassador_schools",
]


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
        for step in STEPS:
            self.stdout.write(f"{step}…")
            call_command(step, **self._options_for(step, options))
        self.stdout.write("remap_training_experience_schools…")
        call_command("remap_training_experience_schools")
        self.stdout.write("link_training_experience_formations…")
        call_command("link_training_experience_formations")

    def _enqueue(self, *, sample):
        """A chain, not a group: every step needs the previous one, and retrying one step
        must not re-download the 110 MB the others already fetched."""
        chain(
            import_onisep_schools_task.si(sample=sample),
            import_onisep_formations_task.si(sample=sample),
            import_onisep_formation_actions_task.si(sample=sample),
            flag_training_ambassador_schools_task.si(),
        ).delay()
        self.stdout.write(self.style.SUCCESS("  Import enfilé sur le worker."))

    def _options_for(self, step, options):
        """Only the Onisep imports have a sample counterpart; the ambassadrice list is the
        same curated file either way."""
        step_options = {"if_empty": options["if_empty"]}
        if step != "flag_training_ambassador_schools":
            step_options["sample"] = options["sample"]
        return step_options
