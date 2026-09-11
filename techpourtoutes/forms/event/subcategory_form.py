from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import Event


class EventSubcategoryForm(forms.Form):
    # The blank choice is the select's placeholder: the component renders it on the trigger and
    # leaves it out of the list. Being required, the field rejects it as a value.
    subcategory = forms.ChoiceField(
        choices=[("", _("Sélectionner une option")), *Event.Subcategory.choices],
        label=_("Quel type d'événement voulez-vous proposer ?"),
    )
    subcategory_other = forms.CharField(
        required=False, label=_("Veuillez préciser le type d'événement")
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("subcategory") == Event.Subcategory.OTHER and not cleaned_data.get(
            "subcategory_other"
        ):
            self.add_error("subcategory_other", _("Précisez le type d'événement."))
        return cleaned_data

    @property
    def resolved_subcategory(self):
        """ "Autre" is a prompt, not a value: what she typed is what the event carries."""
        if self.cleaned_data["subcategory"] == Event.Subcategory.OTHER:
            return self.cleaned_data["subcategory_other"]
        return self.cleaned_data["subcategory"]
