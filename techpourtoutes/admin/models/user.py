from django.contrib import admin

from techpourtoutes.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    readonly_fields = (
        "email",
        "last_login",
        "created_at",
        "updated_at",
        "brevo_sync_enabled",
    )
    fieldsets = (
        ("Infos personnelles", {"fields": ("first_name", "last_name", "email")}),
        (
            "Autres infos",
            {
                "fields": (
                    "last_login",
                    "created_at",
                    "updated_at",
                    "brevo_sync_enabled",
                    "is_active",
                )
            },
        ),
    )

    list_display = ("first_name", "last_name", "email", "created_at")
    list_display_links = list_display
    search_fields = ("first_name", "last_name", "email")
    list_filter = (("created_at", admin.DateFieldListFilter),)
