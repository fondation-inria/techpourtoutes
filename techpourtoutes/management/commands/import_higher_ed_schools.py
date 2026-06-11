import csv
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from techpourtoutes.models import HigherEdSchool

DEFAULT_PATH = settings.BASE_DIR / "data" / "higher_ed_schools.csv"


class Command(BaseCommand):
    help = "Import higher-ed schools from the CSV into the HigherEdSchool table"

    def add_arguments(self, parser):
        parser.add_argument("--path", default=str(DEFAULT_PATH))

    def handle(self, *args, **options):
        imported = sum(self._import_row(row) for row in self._read_rows(options["path"]))
        self.stdout.write(self.style.SUCCESS(f"  {imported} établissements importés."))

    def _read_rows(self, path):
        with open(path, encoding="utf-8") as file:
            return list(csv.DictReader(file))

    def _import_row(self, row):
        school = HigherEdSchool(
            full_name=self._collapse_whitespace(row["Etablissement"]),
            name=row["Acronyme"].strip(),
            siret=row["Siret"].strip(),
            uai=row["UAI"].strip(),
            conferences=self._parse_conferences(row["Conférence"]),
        )
        try:
            school.save()
        except ValidationError:
            return False  # already imported — the model decides what "duplicate" means
        return True

    def _collapse_whitespace(self, value):
        return re.sub(r"\s+", " ", value).strip()

    def _parse_conferences(self, value):
        return [item.strip() for item in value.split(",") if item.strip()]
