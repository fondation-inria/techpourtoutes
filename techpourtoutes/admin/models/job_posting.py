from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models import JobPosting

from ..filters import JobPostingCategoryFilter
from ..read_only import ReadOnlyAdminMixin


@admin.register(JobPosting)
class JobPostingAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("title", "company_name", "source", "category_labels", "contract_type")
    list_display_links = list_display
    search_fields = ("title", "company_name")
    list_filter = ("source", JobPostingCategoryFilter, "contract_type")
    fieldsets = (
        (
            "Informations générales",
            {
                "fields": (
                    "source",
                    "category_labels",
                    "contract_type",
                    "domains",
                )
            },
        ),
        (
            "Détail de l'offre",
            {
                "fields": (
                    "title",
                    "company_name",
                    "company_logo",
                    "description",
                    "duration",
                    "postal_code",
                    "cog_code",
                    "city",
                )
            },
        ),
        (
            "Informations techniques",
            {
                "fields": (
                    "url",
                    "published_at",
                    "source_updated_at",
                    "external_id",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = ("description", "category_labels", "created_at", "updated_at")

    @admin.display(description=_("description"))
    def description(self, job_posting):
        """Sanitised by the import, down to the tags it lays itself out with."""
        return mark_safe(job_posting.description)

    @admin.display(description=_("catégories"))
    def category_labels(self, job_posting):
        return ", ".join(str(JobPosting.Category(value).label) for value in job_posting.categories)
