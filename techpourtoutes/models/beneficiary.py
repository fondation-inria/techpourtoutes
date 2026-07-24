from django.db import models
from django.utils.translation import gettext_lazy as _

from techpourtoutes.signals import connect_brevo_sync

from .user import User


class Beneficiary(User):
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("date de naissance"))

    class Meta:
        verbose_name = _("bénéficiaire")
        verbose_name_plural = _("bénéficiaires")

    def save(self, *args, **kwargs):
        if not self.pk:
            self.set_unusable_password()
            self.civility = User.Civility.MADAME
        super().save(*args, **kwargs)


connect_brevo_sync(Beneficiary)
