from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from techpourtoutes.models import Beneficiary
from techpourtoutes.services.beneficiary.create_mentoree import CreateMentoree

from ..filters import MentoringStatusFilter
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
        "validate_mentoring_list_button",
        "validate_mentoring_form_button",
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
                    "legal_representative_name",
                    "legal_representative_email",
                    "jobirl_user_id",
                    "validate_mentoring_form_button",
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
        "validate_mentoring_list_button",
    )
    list_display_links = list_display[:-1]
    search_fields = ("first_name", "last_name", "email")
    list_filter = (MentoringStatusFilter, ("created_at", admin.DateFieldListFilter))
    inlines = [TrainingExperienceInline, BeneficiarySavedEventInline]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is not None and obj.jobirl_user_id:
            readonly_fields = (
                *readonly_fields,
                "legal_representative_name",
                "legal_representative_email",
            )
        return readonly_fields

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

    def response_change(self, request, obj):
        """The button belongs to the change form: any edit it travels with is already saved by
        the time this runs, so Jobirl is registered against the beneficiary as just corrected."""
        if "_validate_mentoring" in request.POST:
            result = CreateMentoree(beneficiary=obj)
            if result.failure:
                for error in result.errors:
                    messages.error(request, error)
            else:
                messages.success(request, f"{obj.email} a été inscrite à Jobirl.")
            return self.response_post_save_change(request, obj)
        return super().response_change(request, obj)

    @admin.display(description=_("demande de mentorat"))
    def validate_mentoring_list_button(self, obj):
        if obj.jobirl_user_id or not obj.legal_representative_email:
            return "—"
        url = reverse("admin:beneficiary_validate_mentoring", args=[obj.pk])
        return format_html(
            '<button type="submit" formaction="{}" class="button" '
            "onclick=\"return confirm('Confirmer la validation du mentorat ?');\">"
            "Valider et envoyer à Jobirl</button>",
            url,
        )

    @admin.display(description=_("demande de mentorat"))
    def validate_mentoring_form_button(self, obj):
        if obj.jobirl_user_id or not obj.legal_representative_email:
            return "—"
        return mark_safe(
            '<button type="submit" name="_validate_mentoring" class="button" '
            "onclick=\"return confirm('Confirmer la validation du mentorat ?');\">"
            "Valider et envoyer à Jobirl</button>"
        )
