from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from .user import User


class Mentor(User):
    phone = PhoneNumberField(region="FR", verbose_name=_("téléphone"))
    professional_situation = models.CharField(
        max_length=255, verbose_name=_("situation professionnelle")
    )
    structure_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("nom de la structure")
    )
    job_title = models.CharField(max_length=255, verbose_name=_("métier"))
    postal_code = models.CharField(
        max_length=5,
        validators=[RegexValidator(r"^\d{5}$", _("Entrez un code postal valide à 5 chiffres."))],
        verbose_name=_("code postal"),
    )

    class Meta:
        verbose_name = _("mentor")
        verbose_name_plural = _("mentors")

    def save(self, *args, **kwargs):
        if not self.pk:
            self.set_unusable_password()
        super().save(*args, **kwargs)
