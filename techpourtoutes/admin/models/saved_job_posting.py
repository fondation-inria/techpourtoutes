from techpourtoutes.models import SavedJobPosting

from ..read_only import ReadOnlyTabularInline


class BeneficiarySavedJobPostingInline(ReadOnlyTabularInline):
    """On a beneficiary: the job postings she put aside."""

    model = SavedJobPosting
    fields = ("job_posting", "created_at")
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("job_posting")


class JobPostingSavedByInline(ReadOnlyTabularInline):
    """On a job posting: who put it aside."""

    model = SavedJobPosting
    fields = ("beneficiary", "created_at")
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("beneficiary")
