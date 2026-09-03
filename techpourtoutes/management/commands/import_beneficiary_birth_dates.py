import csv
import sys
from datetime import date

from django.core.management.base import BaseCommand

from techpourtoutes.models import Beneficiary


class Command(BaseCommand):
    help = "Renseigne la date de naissance des bénéficiaires Faveod"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", help="Chemin du fichier CSV, ou '-' pour lire sur stdin")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Analyse et valide les lignes sans rien écrire en base",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — aucune écriture en base."))

        updated = not_found = invalid = 0

        for row in csv.DictReader(self._read(options["csv_file"])):
            user_id = (row.get("user_id") or "").strip()
            birth_date = self._parse_birth_date(row.get("birth_date"))
            if not user_id or not birth_date:
                invalid += 1
                continue

            beneficiary = Beneficiary.objects.filter(faveod_id=user_id).first()
            if beneficiary is None:
                not_found += 1
                continue
            beneficiary.birth_date = birth_date
            if not dry_run:
                beneficiary.save(update_fields=["birth_date"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTerminé — mis à jour: {updated}, introuvables: {not_found}, "
                f"lignes invalides: {invalid}"
            )
        )

    @staticmethod
    def _read(csv_file):
        if csv_file == "-":
            return sys.stdin
        return open(csv_file, newline="", encoding="utf-8")

    @staticmethod
    def _parse_birth_date(raw):
        if not raw:
            return None
        try:
            return date.fromisoformat(raw.strip())
        except ValueError:
            return None
