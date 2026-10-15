from django import forms
from django.utils.translation import gettext_lazy as _

from techpourtoutes.validators import POSTAL_CODE_VALIDATOR

from ...models import Pro
from ..fields import PhoneNumberField
from .workshop_request_form import OTHER_SCHOOL_MISSION, OUTSIDE_SCHOOL_JOBS


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

    def __init__(self, *args, workshop=None, pro=None, **kwargs):
        """`workshop` holds the answers of the workshop request. When she works at its school,
        her structure is that school and her job the function she gave, unless the list had none
        for it; the school's postal code is only a suggestion.

        `pro` is the pro taking on one more engagement: only what she has not given yet is asked.

        What is already known is not asked: its field is removed, its value kept in `known` and
        merged back into the cleaned data — whatever is posted for it."""
        super().__init__(*args, **kwargs)
        self.known = {}
        if pro:
            self._know(**self._given_by(pro))
        if workshop and workshop["job_title"] not in OUTSIDE_SCHOOL_JOBS:
            self._know(
                structure_type=Pro.StructureType.SCHOOL, structure_name=workshop["school_label"]
            )
            if workshop["job_title"] != OTHER_SCHOOL_MISSION:
                self._know(job_title=workshop["job_title"])
            self.initial = {"postal_code": workshop["postal_code"], **self.initial}

    @property
    def asks_anything(self):
        return bool(self.fields)

    @property
    def structure_type_value(self):
        """Known or answered: whether her structure name is asked depends on it."""
        if "structure_type" in self.fields:
            return self["structure_type"].value()
        return self.known["structure_type"]

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data.update(self.known)
        structure_type = cleaned_data.get("structure_type")
        if structure_type in Pro.WITHOUT_STRUCTURE:
            cleaned_data["structure_name"] = ""
        elif structure_type and not cleaned_data.get("structure_name"):
            self.add_error("structure_name", _("Ce champ est obligatoire."))
        return cleaned_data

    def _given_by(self, pro):
        given = {name: getattr(pro, name) for name in self.fields if getattr(pro, name)}
        if pro.structure_type in Pro.WITHOUT_STRUCTURE:
            given["structure_name"] = ""
        return given

    def _know(self, **values):
        self.known.update(values)
        for name in values:
            del self.fields[name]
