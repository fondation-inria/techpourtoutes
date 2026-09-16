from django import forms
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models import Event


class AddressSearchWidget(forms.Select):
    """An empty select the Géoplateforme fills, on the admin's own select2: picking a hit writes
    the geocoded columns, which nothing else in the change form may write."""

    class Media:
        js = (
            "admin/js/vendor/jquery/jquery.min.js",
            "admin/js/vendor/select2/select2.full.min.js",
            "admin/js/vendor/select2/i18n/fr.js",
            "admin/js/jquery.init.js",
            "js/admin_address_search.js",
        )
        css = {
            "screen": (
                "admin/css/vendor/select2/select2.min.css",
                "admin/css/autocomplete.css",
            )
        }

    def __init__(self, attrs=None):
        super().__init__(
            {
                "class": "admin-autocomplete",
                "style": "width: 40em; max-width: 100%;",
                "data-ajax-url": reverse_lazy("admin:event_search_addresses"),
                **(attrs or {}),
            }
        )


class SubcategoryWidget(forms.MultiWidget):
    """A labeled dropdown plus the free text "Autre" needs — mirrors the public funnel's
    `EventSubcategoryForm`, but as one widget: the admin form has a single `subcategory` column
    to round-trip, not two separate ones."""

    def __init__(self, attrs=None):
        widgets = [
            forms.Select(choices=[("", _("Sélectionner une option")), *Event.Subcategory.choices]),
            forms.TextInput(attrs={"placeholder": _("Si « Autre », précisez…")}),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if not value:
            return [None, None]
        if value in Event.Subcategory.values:
            return [value, ""]
        return [Event.Subcategory.OTHER, value]


class SubcategoryField(forms.MultiValueField):
    widget = SubcategoryWidget

    def __init__(self, **kwargs):
        fields = [
            forms.ChoiceField(choices=Event.Subcategory.choices),
            forms.CharField(required=False),
        ]
        super().__init__(fields=fields, require_all_fields=False, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return ""
        subcategory, other = data_list
        if subcategory == Event.Subcategory.OTHER:
            if not other:
                raise forms.ValidationError(_("Précisez le type d'événement."))
            return other
        return subcategory
