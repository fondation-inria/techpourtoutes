from django.contrib import admin

from techpourtoutes.models import Beneficiary

from ..filters import MentoringStatusFilter
from .legal_representative_authorization import LegalRepresentativeAuthorizationInline
from .saved_event import BeneficiarySavedEventInline
from .training_experience import TrainingExperienceInline
from .user import PERSONAL_FIELDS, AccountCreationFieldsMixin


@admin.register(Beneficiary)
class BeneficiaryAdmin(AccountCreationFieldsMixin, admin.ModelAdmin):
    readonly_fields = (
        "last_login",
        "created_at",
        "updated_at",
        "jobirl_user_id",
    )
    fieldsets = (
        (
            "Infos personnelles",
            {"fields": (*PERSONAL_FIELDS, "birth_date")},
        ),
        (
            "Mentorat",
            {"fields": ("jobirl_user_id",)},
        ),
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

    list_display = (
        "first_name",
        "last_name",
        "email",
        "birth_date",
        "created_at",
    )
    list_display_links = list_display
    search_fields = ("first_name", "last_name", "email")
    list_filter = (MentoringStatusFilter, ("created_at", admin.DateFieldListFilter))
    inlines = [
        TrainingExperienceInline,
        BeneficiarySavedEventInline,
        LegalRepresentativeAuthorizationInline,
    ]
