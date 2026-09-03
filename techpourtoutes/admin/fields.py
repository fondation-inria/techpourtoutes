from django import forms
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models import Event


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
