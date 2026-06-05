from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from ..models import Pro


class AccountEditForm(forms.Form):
    first_name = forms.CharField(label=_("Prénom*"))
    last_name = forms.CharField(label=_("Nom*"))
    phone = PhoneNumberField(region="FR", label=_("Numéro de téléphone"), required=False)
    professional_situation = forms.ChoiceField(
        label=_("Situation professionnelle*"),
        choices=[("", _("Sélectionner une option")), *Pro.ProfessionalSituation.choices],
    )
    structure_name = forms.CharField(label=_("Structure"), required=False)
    job_title = forms.CharField(label=_("Métier*"))
    postal_code = forms.CharField(
        label=_("Code postal*"),
        validators=[RegexValidator(r"^\d{5}$", _("Entrez un code postal valide à 5 chiffres."))],
    )

    def __init__(self, *args, pro=None, **kwargs):
        if pro is not None:
            kwargs.setdefault(
                "initial",
                {
                    "first_name": pro.first_name,
                    "last_name": pro.last_name,
                    "phone": pro.phone.as_national if pro.phone else "",
                    "professional_situation": pro.professional_situation,
                    "structure_name": pro.structure_name,
                    "job_title": pro.job_title,
                    "postal_code": pro.postal_code,
                },
            )
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("professional_situation") == "working":
            if not cleaned_data.get("structure_name"):
                self.add_error("structure_name", _("Ce champ est obligatoire."))
        return cleaned_data

    def save(self, pro):
        data = self.cleaned_data
        pro.first_name = data["first_name"]
        pro.last_name = data["last_name"]
        pro.phone = data["phone"]
        pro.professional_situation = data["professional_situation"]
        pro.structure_name = data["structure_name"]
        pro.job_title = data["job_title"]
        pro.postal_code = data["postal_code"]
        pro.save()
        return pro
