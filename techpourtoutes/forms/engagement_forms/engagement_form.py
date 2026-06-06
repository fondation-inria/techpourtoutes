from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from ...models import Pro
from .base_engagement_form import BaseEngagementForm


class EngagementForm(BaseEngagementForm):
    pro_fields = (
        "phone",
        "postal_code",
        "professional_situation",
        "structure_name",
        "job_title",
    )
    prefill_fields = pro_fields

    phone = PhoneNumberField(region="FR", label=_("Votre n° de téléphone*"))
    postal_code = forms.CharField(
        label=_("Votre code postal*"),
        validators=[RegexValidator(r"^\d{5}$", _("Entrez un code postal valide à 5 chiffres."))],
    )
    professional_situation = forms.ChoiceField(
        label=_("Votre situation professionnelle*"),
        choices=[("", _("Sélectionner une option"))]
        + [c for c in Pro.ProfessionalSituation.choices if c[0] != "student"],
    )
    structure_name = forms.CharField(label=_("Nom de votre structure*"), required=False)
    job_title = forms.CharField(label=_("Votre métier*"))

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("professional_situation") == "working":
            structure_fields = ("structure_name",)
            for field in structure_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, _("Ce champ est obligatoire."))
        return cleaned_data
