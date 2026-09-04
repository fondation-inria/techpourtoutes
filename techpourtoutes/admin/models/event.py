from django import forms
from django.contrib import admin, messages
from django.contrib.admin.views.main import ChangeList
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from simple_history.admin import SimpleHistoryAdmin

from techpourtoutes.models import Event
from techpourtoutes.services.event.moderate_event import ModerateEvent

from ..fields import SubcategoryField

_DECISION_LABELS = {
    Event.Status.APPROVED: _("publié"),
    Event.Status.REJECTED: _("refusé"),
}


class _DecidedEventChangeList(ChangeList):
    """A pending event is not yet decided: it stays out of the searchable/filterable list,
    surfaced separately above it instead — see `EventAdmin.changelist_view`.

    Scoped here rather than through `ModelAdmin.get_queryset`, which also backs `get_object`:
    excluding pending events there would make an individual one unreachable to moderate."""

    def get_queryset(self, request, exclude_parameters=None):
        return (
            super().get_queryset(request, exclude_parameters).exclude(status=Event.Status.PENDING)
        )


class EventAdminForm(forms.ModelForm):
    subcategory = SubcategoryField(label=_("Sous-catégorie"))

    class Meta:
        model = Event
        fields = (
            "created_by",
            "title",
            "organizer",
            "description",
            "subcategory",
            "status",
            "access_type",
            "registration_url",
            "price",
            "location_type",
            "online_url",
            "start_date",
            "start_time",
            "end_date",
            "end_time",
            "address",
            "postal_code",
            "city",
            "cog_code",
            "longitude",
            "latitude",
            "ban_id",
        )


@admin.register(Event)
class EventAdmin(SimpleHistoryAdmin):
    form = EventAdminForm
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
                    "subcategory",
                    "status",
                    "access_type",
                    "registration_url",
                    "price",
                    "location_type",
                    "online_url",
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
        "subcategory_label",
        "start_date",
        "city",
        "status",
        "created_by",
    )
    list_display_links = list_display
    search_fields = ("title", "organizer", "city", "created_by__email")
    list_filter = ("status", "subcategory", "location_type", "access_type")

    @admin.display(description=_("catégorie"))
    def category_label(self, obj):
        return obj.category_label

    @admin.display(description=_("sous-catégorie"))
    def subcategory_label(self, obj):
        return obj.subcategory_label

    def get_fieldsets(self, request, obj=None):
        """While an event is pending, its status only ever moves through the Publier/Refuser
        buttons — showing the raw field here would invite hand-editing around them."""
        fieldsets = super().get_fieldsets(request, obj)
        if obj is not None and obj.status == Event.Status.PENDING:
            fieldsets = tuple(
                (
                    title,
                    {**options, "fields": tuple(f for f in options["fields"] if f != "status")},
                )
                for title, options in fieldsets
            )
        return fieldsets

    def get_changelist(self, request, **kwargs):
        return _DecidedEventChangeList

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "pending_events": Event.objects.filter(status=Event.Status.PENDING).order_by(
                "created_at"
            ),
        }
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        return [
            path(
                "<uuid:event_id>/moderer/",
                self.admin_site.admin_view(require_POST(self.moderate)),
                name="event_moderate",
            ),
            *super().get_urls(),
        ]

    def moderate(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        status = request.POST.get("decision")
        comment = request.POST.get("comment", "")
        result = ModerateEvent(event=event, status=status, comment=comment)
        if result.failure:
            for error in result.errors:
                messages.error(request, error)
        else:
            label = _DECISION_LABELS.get(status, status)
            messages.success(request, f"L'événement « {event.title} » a été {label}.")
        return redirect(reverse("admin:techpourtoutes_event_change", args=[event.pk]))
