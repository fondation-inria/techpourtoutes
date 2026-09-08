from django import forms
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.http import JsonResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from techpourtoutes.models import Event
from techpourtoutes.services.event.moderate_event import ModerateEvent
from techpourtoutes.services.geoplateforme_api.search_addresses import SearchAddresses

from ..fields import AddressSearchWidget, SubcategoryField

# The submit buttons the moderation panel adds to the change form, and what each decides.
_DECISIONS = {
    "_publish": Event.Status.APPROVED,
    "_reject": Event.Status.REJECTED,
}

_DECISION_LABELS = {
    Event.Status.APPROVED: _("publié"),
    Event.Status.REJECTED: _("refusé"),
}

# Written by the address search, never typed: a place named by hand is what the moderation is
# there to replace, and a half-typed one would carry the coordinates of the last search.
# `readonly` rather than `ModelAdmin.readonly_fields`, which would drop them from the form —
# Django then skips every constraint referencing them, approval's two among them.
SEARCH_ONLY_FIELDS = (
    "poi_name",
    "address",
    "postal_code",
    "city",
    "cog_code",
    "longitude",
    "latitude",
    "ban_id",
)


def _decision_from(data):
    return next((status for key, status in _DECISIONS.items() if key in data), None)


def _option(hit):
    """The dropdown tells its options apart by id, and silently declines to reselect the one it
    already holds: identify the place, never its rank, or the top hit of every search looks
    like the selected one. A hit always carries coordinates — the search drops those without."""
    return {
        "id": f"{hit['longitude']},{hit['latitude']} {hit['label']}",
        "text": hit["label"],
        **hit,
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
    address_search = forms.CharField(
        required=False,
        label=_("Rechercher une adresse ou un lieu"),
        help_text=_("Sélectionnez un résultat pour renseigner les champs ci-dessous."),
        widget=AddressSearchWidget,
    )

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
            "poi_name",
            "address",
            "postal_code",
            "city",
            "cog_code",
            "longitude",
            "latitude",
            "ban_id",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Read before `_post_clean` moves the instance to the status a decision aims at.
        self.awaiting_decision = self.instance.status == Event.Status.PENDING
        for name in SEARCH_ONLY_FIELDS:
            self.fields[name].widget.attrs["readonly"] = True

    @property
    def decision(self):
        """Publier and Refuser are submit buttons of this very form, so the decision arrives
        with the edited fields and goes through the validation any other save goes through."""
        return _decision_from(self.data)

    def _post_clean(self):
        """The status the decision aims at has to be on the instance before it is validated:
        it is what the approval constraints hinge on."""
        if self.decision:
            self.instance.status = self.decision
        super()._post_clean()

    def _get_validation_exclusions(self):
        """`status` is not a form field while the event is pending, and Django skips every
        constraint referencing an excluded field — here, both approval constraints."""
        return super()._get_validation_exclusions() - {"status"}


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
                    "address_search",
                    "poi_name",
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

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        """`original` carries the status the submitted decision aimed at, not the one on file:
        a decision the form refused has to be offered again, next to what it refused."""
        context["awaiting_decision"] = change and context["adminform"].form.awaiting_decision
        return super().render_change_form(request, context, add, change, form_url, obj)

    def save_model(self, request, obj, form, change):
        """A decision saves the event like any other change, then tells its author."""
        if form.decision:
            ModerateEvent(event=obj, status=form.decision, comment=request.POST.get("comment", ""))
        else:
            super().save_model(request, obj, form, change)

    def response_change(self, request, obj):
        """A decision is not just any change: say which one was taken."""
        decision = _decision_from(request.POST)
        if decision:
            self.message_user(
                request, f"L'événement « {obj.title} » a été {_DECISION_LABELS[decision]}."
            )
            return self.response_post_save_change(request, obj)
        return super().response_change(request, obj)

    def get_urls(self):
        return [
            path(
                "recherche-adresses/",
                self.admin_site.admin_view(self.search_addresses),
                name="event_search_addresses",
            ),
            *super().get_urls(),
        ]

    def search_addresses(self, request):
        """The public autocomplete answers HTML to htmx; select2 wants JSON, and the moderation
        wants the endpoint behind the admin's own permission check."""
        result = SearchAddresses(query=request.GET.get("q", "").strip())
        return JsonResponse({"results": [_option(hit) for hit in result.addresses]})
