import csv
import re
from datetime import datetime, timezone

import phonenumbers
from django.core.management.base import BaseCommand

from techpourtoutes.models import Pro

WORK_STATUS_MAP = {
    "En recherche d'emploi": Pro.ProfessionalSituation.JOBLESS,
    "Retraité": Pro.ProfessionalSituation.RETIRED,
}

GENDER_MAP = {
    "1": Pro.Civility.MADAME,
    "2": Pro.Civility.MONSIEUR,
}


class Command(BaseCommand):
    help = "Import pros from a Faveod CSV export"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", help="Path to the Faveod CSV file")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate rows without writing to the database",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes will be written."))

        created = skipped = errors = 0

        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                faveod_id = int(row["id"])

                if Pro.objects.filter(faveod_id=faveod_id).exists():
                    self.stdout.write(f"  faveod_id={faveod_id} already exists, skipping.")
                    skipped += 1
                    continue

                if Pro.objects.filter(email=row["email"]).exists():
                    self.stdout.write(
                        f"  email={row['email']} already exists (faveod_id={faveod_id}), skipping."
                    )
                    skipped += 1
                    continue

                try:
                    pro = self._build_pro(row, faveod_id)
                    if not dry_run:
                        pro.save()
                        if created_at := self._parse_created_at(row.get("created_at")):
                            Pro.objects.filter(pk=pro.pk).update(created_at=created_at)
                    created += 1
                except Exception as exc:
                    self.stderr.write(
                        self.style.ERROR(f"  faveod_id={faveod_id} ({row.get('email')}): {exc}")
                    )
                    errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTerminé — créés: {created}, ignorés: {skipped}, erreurs: {errors}"
            )
        )

    def _build_pro(self, row, faveod_id):
        engagements = []

        if "5" in re.split(r"[,\s]+", row.get("user_types", "")):
            engagements.append(Pro.Engagement.WORKSHOPS)

        if row.get("agreed_to_be_contacted", "").lower() == "true":
            engagements.append(Pro.Engagement.WORK_AMBASSADOR)

        jobirl_user_id = None
        jobirl_user_token = ""
        if row.get("jobirl_user_id"):
            jobirl_user_id = int(row["jobirl_user_id"])
            engagements.append(Pro.Engagement.MENTOR)
        if row.get("jobirl_user_token"):
            jobirl_user_token = row["jobirl_user_token"]

        return Pro(
            username=row["email"],
            email=row["email"],
            first_name=row.get("first_name", ""),
            last_name=row.get("last_name", ""),
            civility=GENDER_MAP.get(row.get("gender", ""), Pro.Civility.MADAME),
            phone=self._normalize_phone(row.get("phone_number", "")),
            professional_situation=WORK_STATUS_MAP.get(
                row.get("work_status", ""), Pro.ProfessionalSituation.WORKING
            ),
            structure_name=row.get("organization_name", ""),
            job_title=row.get("position", ""),
            postal_code=row.get("zip_code", "") or "",
            faveod_id=faveod_id,
            jobirl_user_id=jobirl_user_id,
            jobirl_user_token=jobirl_user_token,
            engagements=engagements,
        )

    @staticmethod
    def _normalize_phone(raw):
        if not raw:
            return ""
        cleaned = re.sub(r"[\s.\-]", "", raw)
        # "+33 0XXXXXXXXX" → "+33XXXXXXXXX" (strip double country-code prefix)
        cleaned = re.sub(r"^\+330", "+33", cleaned)
        try:
            parsed = phonenumbers.parse(cleaned, "FR")
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            pass
        return cleaned

    @staticmethod
    def _parse_created_at(raw):
        if not raw:
            return None
        # Format: "2025-06-18 14:48:37 UTC"
        dt = datetime.strptime(raw.replace(" UTC", "").strip(), "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
