from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel, BaseQuerySet
from .beneficiary import Beneficiary
from .job_posting import JobPosting


class ClickedJobPostingQuerySet(BaseQuerySet):
    def toggle(self, job_posting, beneficiary):
        """Mark a job posting clicked, or take it back. True when it is now clicked."""
        deleted, _ = self.filter(job_posting=job_posting, beneficiary=beneficiary).delete()
        if deleted:
            return False
        self.create(job_posting=job_posting, beneficiary=beneficiary)
        return True


class ClickedJobPosting(BaseModel):
    """One job posting a beneficiary clicked."""

    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="clicks",
        verbose_name=_("offre d'emploi"),
    )
    beneficiary = models.ForeignKey(
        Beneficiary,
        on_delete=models.CASCADE,
        related_name="job_posting_clicks",
        verbose_name=_("bénéficiaire"),
    )

    objects = ClickedJobPostingQuerySet.as_manager()

    class Meta:
        verbose_name = _("offre d'emploi cliquée")
        verbose_name_plural = _("offres d'emploi cliquées")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["job_posting", "beneficiary"],
                name="unique_clicked_job_posting_per_beneficiary",
            ),
        ]

    def __str__(self):
        return f"{self.beneficiary.full_name} – {self.job_posting.title}"
