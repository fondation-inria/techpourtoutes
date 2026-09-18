from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models import Pro

from ..filters import EngagementFilter
from ..stats import pro_stats
from .training_experience import TrainingExperienceInline
from .user import PERSONAL_FIELDS, AccountCreationFieldsMixin
from .workshop_request import WorkshopRequestInline


@admin.register(Pro)
class ProAdmin(AccountCreationFieldsMixin, admin.ModelAdmin):
    readonly_fields = (
        "last_login",
        "created_at",
        "updated_at",
        "jobirl_user_id",
        "faveod_id",
        "display_engagements",
    )
    fieldsets = (
        (
            "Infos personnelles",
            {
                "fields": (
                    *PERSONAL_FIELDS,
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
        (
            "Accès à l'administration",
            {
                "fields": ("groups",),
                "description": (
                    "Un rôle ouvre l'accès à l'administration, limité à ce qu'il porte. "
                    "Sans aucun rôle, le compte n'y a pas accès."
                ),
            },
        ),
    )

    list_display = ("first_name", "last_name", "email", "display_engagements", "created_at")
    list_display_links = list_display
    search_fields = ("first_name", "last_name", "email")
    list_filter = (EngagementFilter, ("created_at", admin.DateFieldListFilter))
    inlines = [TrainingExperienceInline, WorkshopRequestInline]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """A role is ticked, not picked from a list: checkboxes read as selected on their own,
        and the wrapper's add/change/delete shortcuts are dropped."""
        if db_field.name == "groups":
            kwargs["widget"] = forms.CheckboxSelectMultiple
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "groups":
            formfield.widget.can_add_related = False
            formfield.widget.can_change_related = False
            formfield.widget.can_delete_related = False
            formfield.widget.can_view_related = False
        return formfield

    @admin.display(description=_("engagements"))
    def display_engagements(self, obj):
        labels = dict(Pro.Engagement.choices)
        return ", ".join(str(labels[engagement]) for engagement in obj.engagements) or "—"

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), "stats": pro_stats()}
        return super().changelist_view(request, extra_context=extra_context)
