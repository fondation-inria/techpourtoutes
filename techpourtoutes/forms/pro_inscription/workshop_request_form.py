from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import WorkshopRequest
from ..engagement.workshop_request_form import FONCTION_CHOICES
from ..mixins import MissingRecordMixin


class ProWorkshopRequestForm(MissingRecordMixin, forms.Form):
    # Its school, job and postal code are not those of the other screens of the funnel, whose
    # answers all land in the same place.
    prefix = "workshop"

    structure_uai = forms.CharField(widget=forms.HiddenInput, required=False)
    school_label = forms.CharField(label=_("Quel est le nom de votre établissement ?*"))
    postal_code = forms.CharField(widget=forms.HiddenInput, required=False)
    school_not_found = forms.BooleanField(widget=forms.HiddenInput, required=False)
    job_title = forms.ChoiceField(label=_("Quel est votre métier ?*"), choices=FONCTION_CHOICES)
    ateliers = forms.MultipleChoiceField(
        label=_("Atelier demandé*"),
        choices=WorkshopRequest.Type.choices,
        widget=forms.CheckboxSelectMultiple,
    )
    remark = forms.CharField(label=_("Remarque"), required=False, widget=forms.Textarea)

    def clean(self):
        """Outside the fallback, the name must come from the autocomplete — hence its UAI."""
        cleaned_data = super().clean()
        if not self.school_not_found and not cleaned_data.get("structure_uai"):
            self.add_error("school_label", _("Sélectionnez un établissement dans la liste."))
        return cleaned_data
