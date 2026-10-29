from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models import JobPosting


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    """Owned by the import, but for `hidden`: the team unpublishes an offer by hand."""

    list_display = ("title", "company_name", "source", "category", "contract_type", "hidden")
    list_display_links = list_display
    search_fields = ("title", "company_name")
    list_filter = ("source", "category", "contract_type", "hidden")
    fieldsets = (
        (
            "Informations générales",
            {
                "fields": (
                    "source",
                    "category",
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
                    "company_logo_preview",
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
                    "hidden",
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

    def get_queryset(self, _request):
        return JobPosting.all_objects.all()

    def has_add_permission(self, _request):
        return False

    def has_delete_permission(self, _request, _obj=None):
        return False

    def get_readonly_fields(self, _request, _obj=None):
        return [field for field in flatten_fieldsets(self.fieldsets) if field != "hidden"]

    @admin.display(description=_("description"))
    def description(self, job_posting):
        """Sanitised by the import, down to the tags it lays itself out with."""
        return mark_safe(job_posting.description)

    @admin.display(description=_("aperçu du logo"))
    def company_logo_preview(self, job_posting):
        """Some logos are served as `application/octet-stream`: an <img> still sniffs them."""
        if job_posting.company_logo:
            return format_html(
                '<img src="{}" alt="" style="max-height: 150px;">', job_posting.company_logo
            )
        else:
            return "-"
