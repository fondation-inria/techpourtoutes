from django.db import models
from django.utils.translation import gettext_lazy as _

from .user import User


class Beneficiary(User):
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("date de naissance"))
    legal_representative_name = models.CharField(
        max_length=150, blank=True, verbose_name=_("nom de la personne responsable légale")
    )
    legal_representative_email = models.EmailField(
        blank=True, verbose_name=_("email de la personne responsable légale")
    )

    class Meta:
        verbose_name = _("bénéficiaire")
        verbose_name_plural = _("bénéficiaires")

    def save(self, *args, **kwargs):
        if not self.pk:
            self.set_unusable_password()
            self.civility = User.Civility.MADAME
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.birth_date = None
        self.legal_representative_name = ""
        self.legal_representative_email = ""
        super().soft_delete()
