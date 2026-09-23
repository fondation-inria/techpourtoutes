from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import Event


class EventSubcategoryForm(forms.Form):
    # The blank choice is the select's placeholder: the component renders it on the trigger and
    # leaves it out of the list. Being required, the field rejects it as a value.
    subcategory = forms.ChoiceField(
        choices=[("", _("Sélectionner une option")), *Event.Subcategory.sorted_choices()],
        label=_("Quel type d'événement voulez-vous proposer ?"),
    )
    subcategory_other = forms.CharField(
        required=False, max_length=22, label=_("Veuillez préciser le type d'événement")
    )

    def __init__(self, *args, event=None, **kwargs):
        if event is not None:
            kwargs.setdefault("initial", self._initial_from_event(event))
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("subcategory") == Event.Subcategory.OTHER and not cleaned_data.get(
            "subcategory_other"
        ):
            self.add_error("subcategory_other", _("Précisez le type d'événement."))
        return cleaned_data

    @property
    def event_fields(self):
        return {"subcategory": self.resolved_subcategory}

    @property
    def resolved_subcategory(self):
        """ "Autre" is a prompt, not a value: what she typed is what the event carries."""
        if self.cleaned_data["subcategory"] == Event.Subcategory.OTHER:
            return self.cleaned_data["subcategory_other"]
        return self.cleaned_data["subcategory"]

    def _initial_from_event(self, event):
        """The mirror of `resolved_subcategory`: an unlisted subcategory is the free text
        typed under "Autre"."""
        listed = event.subcategory in Event.Subcategory.values
        return {
            "subcategory": event.subcategory if listed else Event.Subcategory.OTHER,
            "subcategory_other": "" if listed else event.subcategory,
        }
