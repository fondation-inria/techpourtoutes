from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from techpourtoutes.models import Beneficiary
from techpourtoutes.services.beneficiary.create_mentoree import CreateMentoree

from ..filters import MentoringStatusFilter
from .training_experience import TrainingExperienceInline
from .user import PERSONAL_FIELDS, AccountCreationFieldsMixin


@admin.register(Beneficiary)
class BeneficiaryAdmin(AccountCreationFieldsMixin, admin.ModelAdmin):
    readonly_fields = (
        "last_login",
        "created_at",
        "updated_at",
        "legal_representative_email",
        "jobirl_user_id",
        "mentoring_validation_action",
    )
    fieldsets = (
        (
            "Infos personnelles",
            {"fields": (*PERSONAL_FIELDS, "birth_date")},
        ),
        (
            "Mentorat",
            {
                "fields": (
                    "legal_representative_email",
                    "jobirl_user_id",
                    "mentoring_validation_action",
                )
            },
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
        "mentoring_validation_action",
    )
    list_display_links = list_display[:-1]
    search_fields = ("first_name", "last_name", "email")
    list_filter = (MentoringStatusFilter, ("created_at", admin.DateFieldListFilter))
    inlines = [TrainingExperienceInline]

    def get_urls(self):
        return [
            path(
                "<uuid:beneficiary_id>/valider-mentorat/",
                self.admin_site.admin_view(require_POST(self.validate_mentoring)),
                name="beneficiary_validate_mentoring",
            ),
            *super().get_urls(),
        ]

    def validate_mentoring(self, request, beneficiary_id):
        beneficiary = get_object_or_404(Beneficiary, pk=beneficiary_id)
        result = CreateMentoree(beneficiary=beneficiary)
        if result.failure:
            for error in result.errors:
                messages.error(request, error)
        else:
            messages.success(request, f"{beneficiary.email} a été inscrite à Jobirl.")
        return redirect(reverse("admin:techpourtoutes_beneficiary_changelist"))

    @admin.display(description=_("demande de mentorat"))
    def mentoring_validation_action(self, obj):
        if obj.jobirl_user_id or not obj.legal_representative_email:
            return "—"
        url = reverse("admin:beneficiary_validate_mentoring", args=[obj.pk])
        return format_html(
            '<button type="submit" formaction="{}" class="button" '
            "onclick=\"return confirm('Confirmer la validation du mentorat ?');\">"
            "Valider et envoyer à Jobirl</button>",
            url,
        )
