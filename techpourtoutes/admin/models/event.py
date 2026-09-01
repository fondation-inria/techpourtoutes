from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from techpourtoutes.models import Event


@admin.register(Event)
class EventAdmin(SimpleHistoryAdmin):
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Événement",
            {
                "fields": (
                    "created_by",
                    "title",
                    "organizer",
                    "description",
                    "category",
                    "status",
                    "reservation_type",
                    "price",
                    "location_type",
                    "online_url",
                    "event_url",
                )
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "start_date",
                    "start_time",
                    "end_date",
                    "end_time",
                )
            },
        ),
        (
            "Lieu",
            {
                "fields": (
                    "address",
                    "postal_code",
                    "city",
                    "cog_code",
                    "longitude",
                    "latitude",
                    "ban_id",
                )
            },
        ),
        (
            "Autres infos",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    list_display = (
        "title",
        "category_label",
        "start_date",
        "location_type",
        "city",
        "status",
        "created_by",
    )
    list_display_links = list_display
    search_fields = ("title", "organizer", "city", "created_by__email")
    list_filter = ("status", "category", "location_type", "reservation_type")

    @admin.display(description=_("catégorie"))
    def category_label(self, obj):
        return obj.category_label
