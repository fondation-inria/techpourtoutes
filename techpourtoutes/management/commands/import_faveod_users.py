import csv
import re
from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from techpourtoutes.models import Beneficiary, User
from techpourtoutes.utils.phone import parse_phone

BENEFICIARY_USER_TYPES = {"1", "2"}


class Command(BaseCommand):
    help = "Import beneficiaries from a Faveod CSV export"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", help="Chemin du fichier CSV Faveod")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Analyse et valide les lignes sans rien écrire en base",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — aucune écriture en base."))

        created = skipped = errors = 0

        with open(options["csv_file"], newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if not self._is_beneficiary(row):
                    skipped += 1
                    continue

                try:
                    if self._already_imported(row):
                        skipped += 1
                        continue
                    self._import(row, dry_run)
                    created += 1
                except Exception as exc:
                    self.stderr.write(
                        self.style.ERROR(f"  id={row.get('id')} ({row.get('email')}): {exc}")
                    )
                    errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTerminé — créés: {created}, ignorés: {skipped}, erreurs: {errors}"
            )
        )

    @staticmethod
    def _is_beneficiary(row):
        user_types = set(re.split(r"[,\s]+", row.get("user_types", "")))
        return row.get("active", "").lower() == "true" and bool(
            BENEFICIARY_USER_TYPES & user_types
        )

    def _already_imported(self, row):
        # all_objects and not objects: the default manager hides deactivated accounts, whose
        # email and username would still collide on the unique constraints.
        email = row["email"].strip()
        if User.all_objects.filter(faveod_id=int(row["id"])).exists():
            self.stdout.write(f"  faveod_id={row['id']} existe déjà, ignoré.")
            return True
        if User.all_objects.filter(Q(email=email) | Q(username=email)).exists():
            self.stdout.write(f"  email={email} existe déjà (id={row['id']}), ignoré.")
            return True
        return False

    def _import(self, row, dry_run):
        """Write the row, rolling back on a dry run so it is validated exactly as a real one."""
        beneficiary = self._build_beneficiary(row)
        with transaction.atomic():
            beneficiary.save()
            # created_at is auto_now_add, so the imported date needs a second write.
            if created_at := self._parse_created_at(row.get("created_at")):
                Beneficiary.objects.filter(pk=beneficiary.pk).update(created_at=created_at)
            if dry_run:
                transaction.set_rollback(True)

    def _build_beneficiary(self, row):
        email = row["email"].strip()
        jobirl_user_id = row.get("jobirl_user_id", "").strip()
        return Beneficiary(
            username=email,
            email=email,
            first_name=row.get("first_name", "").strip(),
            last_name=row.get("last_name", "").strip(),
            legal_representative_email=row.get("e_mail_tuteur", "").strip(),
            phone=parse_phone(row.get("phone_number")),
            postal_code=self._normalize_postal_code(row.get("zip_code")),
            faveod_id=int(row["id"]),
            jobirl_user_id=int(jobirl_user_id) if jobirl_user_id else None,
            jobirl_user_token=row.get("jobirl_user_token", "").strip(),
            brevo_sync_enabled=row.get("agreed_to_be_contacted", "").lower() == "true",
        )

    @staticmethod
    def _normalize_postal_code(raw):
        """Keep what `POSTAL_CODE_VALIDATOR` accepts, drop the rest rather than fail the row."""
        digits = re.sub(r"\D", "", raw or "")
        # Spreadsheets eat the leading zero of the 01-09 départements.
        if len(digits) == 4:
            digits = f"0{digits}"
        return digits if len(digits) == 5 else ""

    @staticmethod
    def _parse_created_at(raw):
        if not raw:
            return None
        # Format: "2025-06-18 14:48:37 UTC"
        dt = datetime.strptime(raw.replace(" UTC", "").strip(), "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
