from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel, BaseQuerySet
from .beneficiary import Beneficiary
from .job_posting import JobPosting


class SavedJobPostingQuerySet(BaseQuerySet):
    def toggle(self, job_posting, beneficiary):
        """Put a job posting aside, or take it back out. True when it is now saved."""
        deleted, _ = self.filter(job_posting=job_posting, beneficiary=beneficiary).delete()
        if deleted:
            return False
        self.create(job_posting=job_posting, beneficiary=beneficiary)
        return True


class SavedJobPosting(BaseModel):
    """One job posting a beneficiary put aside."""

    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="saves",
        verbose_name=_("offre d'emploi"),
    )
    beneficiary = models.ForeignKey(
        Beneficiary,
        on_delete=models.CASCADE,
        related_name="job_posting_saves",
        verbose_name=_("bénéficiaire"),
    )

    objects = SavedJobPostingQuerySet.as_manager()

    class Meta:
        verbose_name = _("offre d'emploi sauvegardée")
        verbose_name_plural = _("offres d'emploi sauvegardées")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["job_posting", "beneficiary"],
                name="unique_saved_job_posting_per_beneficiary",
            ),
        ]

    def __str__(self):
        return f"{self.beneficiary.full_name} – {self.job_posting.title}"
