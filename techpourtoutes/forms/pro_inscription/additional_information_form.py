from django import forms
from django.utils.translation import gettext_lazy as _

from techpourtoutes.validators import POSTAL_CODE_VALIDATOR

from ...models import Pro
from ..fields import PhoneNumberField
from .workshop_request_form import OTHER_SCHOOL_MISSION, OUTSIDE_SCHOOL_JOBS

# Those who answer one of these work in no structure to name.
WITHOUT_STRUCTURE = (Pro.StructureType.RETIRED, Pro.StructureType.JOBLESS)


class ProAdditionalInformationForm(forms.Form):
    structure_type = forms.ChoiceField(
        label=_("Dans quel type de structure travaillez-vous ?*"),
        choices=[("", _("Sélectionner une option")), *Pro.StructureType.choices],
    )
    structure_name = forms.CharField(
        label=_("Quel est le nom de votre structure ?*"), required=False
    )
    job_title = forms.CharField(label=_("Quel est votre métier ?*"))
    phone = PhoneNumberField(region="FR", label=_("Votre numéro de téléphone*"))
    postal_code = forms.CharField(
        label=_("Votre code postal*"), validators=[POSTAL_CODE_VALIDATOR]
    )

    def __init__(self, *args, workshop=None, **kwargs):
        """`workshop` holds the answers of the workshop request. When she works at its school,
        her structure is that school and her job the function she gave, unless the list had none
        for it; the school's postal code is only a suggestion."""
        super().__init__(*args, **kwargs)
        if workshop and workshop["job_title"] not in OUTSIDE_SCHOOL_JOBS:
            self._lock(
                structure_type=Pro.StructureType.SCHOOL, structure_name=workshop["school_label"]
            )
            if workshop["job_title"] != OTHER_SCHOOL_MISSION:
                self._lock(job_title=workshop["job_title"])
            self.initial = {"postal_code": workshop["postal_code"], **self.initial}

    def _lock(self, **values):
        self.initial = {**self.initial, **values}
        for name in values:
            self.fields[name].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        structure_type = cleaned_data.get("structure_type")
        if structure_type in WITHOUT_STRUCTURE:
            cleaned_data["structure_name"] = ""
        elif structure_type and not cleaned_data.get("structure_name"):
            self.add_error("structure_name", _("Ce champ est obligatoire."))
        return cleaned_data
