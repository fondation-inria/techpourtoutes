from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models import Pro

from ..filters import EngagementFilter
from ..stats import pro_stats
from .workshop_request import WorkshopRequestInline


@admin.register(Pro)
class ProAdmin(admin.ModelAdmin):
    readonly_fields = (
        "email",
        "last_login",
        "created_at",
        "updated_at",
        "brevo_sync_enabled",
        "jobirl_user_id",
        "faveod_id",
        "display_engagements",
    )
    fieldsets = (
        (
            "Infos personnelles",
            {
                "fields": (
                    "civility",
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "postal_code",
                    "professional_situation",
                    "structure_name",
                    "job_title",
                    "display_engagements",
                )
            },
        ),
        (
            "Autres infos",
            {
                "fields": (
                    "jobirl_user_id",
                    "faveod_id",
                    "last_login",
                    "created_at",
                    "updated_at",
                    "brevo_sync_enabled",
                    "is_active",
                )
            },
        ),
    )

    list_display = ("first_name", "last_name", "email", "display_engagements", "created_at")
    list_display_links = list_display
    search_fields = ("first_name", "last_name", "email")
    list_filter = (EngagementFilter, ("created_at", admin.DateFieldListFilter))

    @admin.display(description=_("engagements"))
    def display_engagements(self, obj):
        labels = dict(Pro.Engagement.choices)
        return ", ".join(str(labels[engagement]) for engagement in obj.engagements) or "—"

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), "stats": pro_stats()}
        return super().changelist_view(request, extra_context=extra_context)

    def get_inlines(self, _request, obj):
        if obj and obj.workshop_requests.exists():
            return [WorkshopRequestInline]
        return []
