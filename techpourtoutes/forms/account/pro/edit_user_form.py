from django import forms
from django.utils.translation import gettext_lazy as _

from techpourtoutes.validators import POSTAL_CODE_VALIDATOR

from ....models import Pro
from ...fields import PhoneNumberField


class ProEditUserForm(forms.Form):
    first_name = forms.CharField(label=_("Prénom*"))
    last_name = forms.CharField(label=_("Nom*"))
    phone = PhoneNumberField(region="FR", label=_("Numéro de téléphone"), required=False)
    structure_type = forms.ChoiceField(
        label=_("Type de structure*"),
        choices=[("", _("Sélectionner une option")), *Pro.StructureType.choices],
    )
    structure_name = forms.CharField(label=_("Structure"), required=False)
    job_title = forms.CharField(label=_("Métier"), required=False)
    postal_code = forms.CharField(
        label=_("Code postal"),
        required=False,
        validators=[POSTAL_CODE_VALIDATOR],
    )

    def __init__(self, *args, pro=None, **kwargs):
        if pro is not None:
            kwargs.setdefault(
                "initial",
                {
                    "first_name": pro.first_name,
                    "last_name": pro.last_name,
                    "phone": pro.phone.as_national if pro.phone else "",
                    "structure_type": pro.structure_type,
                    "structure_name": pro.structure_name,
                    "job_title": pro.job_title,
                    "postal_code": pro.postal_code,
                },
            )
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        structure_type = cleaned_data.get("structure_type")
        if structure_type in Pro.WITHOUT_STRUCTURE:
            cleaned_data["structure_name"] = ""
        elif structure_type and not cleaned_data.get("structure_name"):
            self.add_error("structure_name", _("Ce champ est obligatoire."))
        return cleaned_data

    def save(self, pro):
        data = self.cleaned_data
        pro.first_name = data["first_name"]
        pro.last_name = data["last_name"]
        pro.phone = data["phone"]
        pro.structure_type = data["structure_type"]
        pro.structure_name = data["structure_name"]
        pro.job_title = data["job_title"]
        pro.postal_code = data["postal_code"]
        pro.save()
        return pro
