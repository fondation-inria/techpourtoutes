from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import Event

# Written by the autocomplete, never typed. `address`, `postal_code` and `city` are left out:
# they become visible inputs when the geocoding API is unreachable.
GEOCODED_FIELDS = ("cog_code", "longitude", "latitude", "ban_id")
ADDRESS_FIELDS = ("address", "postal_code", "city", *GEOCODED_FIELDS)


class EventLocationForm(forms.Form):
    location_type = forms.ChoiceField(
        choices=Event.LocationType.choices, label=_("Où se déroule l'événement ?*")
    )
    address = forms.CharField(required=False, label=_("Quelle est l'adresse de l'événement ?*"))
    postal_code = forms.CharField(required=False, label=_("Code postal*"))
    city = forms.CharField(required=False, label=_("Ville*"))
    cog_code = forms.CharField(required=False, widget=forms.HiddenInput)
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput)
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput)
    ban_id = forms.CharField(required=False, widget=forms.HiddenInput)
    address_api_down = forms.BooleanField(required=False, widget=forms.HiddenInput)
    online_url = forms.URLField(
        required=False,
        label=_("Quel est le lien de connexion à l'événement ?"),
        help_text=_("Lien pour rejoindre l'événement"),
    )
    access_type = forms.ChoiceField(
        choices=Event.AccessType.choices, label=_("Quelles sont les modalités d'inscription ?*")
    )
    registration_url = forms.URLField(required=False)
    price = forms.DecimalField(max_digits=8, decimal_places=2, min_value=0, label=_("Tarif*"))

    def clean(self):
        cleaned_data = super().clean()
        self._clean_location(cleaned_data)
        self._clean_registration(cleaned_data)
        return cleaned_data

    def _clean_location(self, cleaned_data):
        """Only one of the two branches survives: she may fill an address then switch to online."""
        if cleaned_data.get("location_type") == Event.LocationType.PHYSICAL:
            cleaned_data["online_url"] = ""
            self._require_address(cleaned_data)
            return
        for field in ADDRESS_FIELDS:
            cleaned_data[field] = None if field in ("longitude", "latitude") else ""

    def _require_address(self, cleaned_data):
        """Without the autocomplete there is nothing to geocode with, so the three parts of the
        address have to be typed in full."""
        required = ("address", "postal_code", "city") if self.api_down else ("address",)
        for field in required:
            if not cleaned_data.get(field):
                self.add_error(field, _("Renseignez l'adresse de l'événement."))

    def _clean_registration(self, cleaned_data):
        if cleaned_data.get("access_type") == Event.AccessType.OPEN:
            cleaned_data["registration_url"] = ""
        elif cleaned_data.get("access_type") and not cleaned_data.get("registration_url"):
            self.add_error("registration_url", _("Renseignez le lien d'inscription."))

    @property
    def api_down(self):
        return self.cleaned_data.get("address_api_down", False)
