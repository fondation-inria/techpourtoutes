from techpourtoutes.models import ClickedJobPosting

from ..read_only import ReadOnlyTabularInline


class BeneficiaryClickedJobPostingInline(ReadOnlyTabularInline):
    """On a beneficiary: the job postings she clicked."""

    model = ClickedJobPosting
    fields = ("job_posting", "created_at")
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("job_posting")


class JobPostingClickedByInline(ReadOnlyTabularInline):
    """On a job posting: who clicked it."""

    model = ClickedJobPosting
    fields = ("beneficiary", "created_at")
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("beneficiary")
