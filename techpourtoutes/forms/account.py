from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from ..models import Mentor


class AccountEditForm(forms.Form):
    first_name = forms.CharField(label=_("Prénom"))
    last_name = forms.CharField(label=_("Nom"))
    phone = PhoneNumberField(region="FR", label=_("Numéro de téléphone"))
    professional_situation = forms.ChoiceField(
        label=_("Situation professionnelle"),
        choices=[("", _("Sélectionner une option")), *Mentor.ProfessionalSituation.choices],
    )
    structure_name = forms.CharField(label=_("Structure"), required=False)
    job_title = forms.CharField(label=_("Métier"))
    postal_code = forms.CharField(
        label=_("Code postal"),
        validators=[RegexValidator(r"^\d{5}$", _("Entrez un code postal valide à 5 chiffres."))],
    )

    def __init__(self, *args, mentor=None, **kwargs):
        if mentor is not None:
            kwargs.setdefault(
                "initial",
                {
                    "first_name": mentor.first_name,
                    "last_name": mentor.last_name,
                    "phone": str(mentor.phone),
                    "professional_situation": mentor.professional_situation,
                    "structure_name": mentor.structure_name,
                    "job_title": mentor.job_title,
                    "postal_code": mentor.postal_code,
                },
            )
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("professional_situation") in ("working", "student"):
            if not cleaned_data.get("structure_name"):
                self.add_error("structure_name", _("Ce champ est obligatoire."))
        return cleaned_data

    def save(self, mentor):
        data = self.cleaned_data
        mentor.first_name = data["first_name"]
        mentor.last_name = data["last_name"]
        mentor.phone = data["phone"]
        mentor.professional_situation = data["professional_situation"]
        mentor.structure_name = data["structure_name"]
        mentor.job_title = data["job_title"]
        mentor.postal_code = data["postal_code"]
        mentor.save()
        return mentor
