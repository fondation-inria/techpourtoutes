from django.db import models
from django.utils.translation import gettext_lazy as _


class StructureType(models.TextChoices):
    ASSOCIATION = "association", _("Association")
    HIGHER_ED = "higher_ed", _("Établissement du supérieur")
    SCHOOL = "school", _("Collège ou lycée")
    COMPANY = "company", _("Entreprise")
    PUBLIC_INSTITUTION = "public_institution", _("Institution publique")
    RETIRED = "retired", _("Je suis à la retraite")
    JOBLESS = "jobless", _("Je suis sans emploi")
