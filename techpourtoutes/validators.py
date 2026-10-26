from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

POSTAL_CODE_VALIDATOR = RegexValidator(r"^\d{5}$", _("Le code postal doit contenir 5 chiffres."))
