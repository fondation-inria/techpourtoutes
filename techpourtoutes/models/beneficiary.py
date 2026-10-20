from django.db import models
from django.utils.translation import gettext_lazy as _

from .user import User


class Beneficiary(User):
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("date de naissance"))
    has_requested_training_ambassador = models.BooleanField(
        default=False, verbose_name=_("a demandé à être mise en contact avec une ambassadrice")
    )

    class Meta:
        verbose_name = _("bénéficiaire")
        verbose_name_plural = _("bénéficiaires")

    @property
    def is_registered_for_mentoring(self):
        return bool(self.jobirl_user_id) or self.has_legal_representative_authorization

    @property
    def has_legal_representative_authorization(self):
        return hasattr(self, "legal_representative_authorization")

    def save(self, *args, **kwargs):
        if not self.pk:
            self.set_unusable_password()
            self.civility = User.Civility.MADAME
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.birth_date = None
        self._forget_legal_representative()
        super().soft_delete()

    def _forget_legal_representative(self):
        if self.has_legal_representative_authorization:
            self.legal_representative_authorization.proof_pdf.delete(save=False)
            self.legal_representative_authorization.delete()
