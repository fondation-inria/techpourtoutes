from django.contrib import admin

from techpourtoutes.models import User

from .training_experience import TrainingExperienceInline

PERSONAL_FIELDS = ("civility", "first_name", "last_name", "email", "phone", "postal_code")


class AccountCreationFieldsMixin:
    """Fields typed when the account is created, then locked — editing them is the funnel's job."""

    CREATE_ONLY_FIELDS = ("email", "brevo_sync_enabled")

    def get_readonly_fields(self, _request, obj=None):
        if obj is None:
            return self.readonly_fields
        return (*self.readonly_fields, *self.CREATE_ONLY_FIELDS)


@admin.register(User)
class UserAdmin(AccountCreationFieldsMixin, admin.ModelAdmin):
    readonly_fields = (
        "last_login",
        "created_at",
        "updated_at",
        "jobirl_user_id",
        "faveod_id",
    )
    fieldsets = (
        (
            "Infos personnelles",
            {"fields": (*PERSONAL_FIELDS, "username")},
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

    list_display = ("first_name", "last_name", "email", "created_at")
    list_display_links = list_display
    search_fields = ("first_name", "last_name", "email")
    list_filter = (("created_at", admin.DateFieldListFilter),)
    inlines = [TrainingExperienceInline]
