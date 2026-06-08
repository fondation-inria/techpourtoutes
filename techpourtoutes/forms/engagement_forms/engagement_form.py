from django import forms
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from ...models import POSTAL_CODE_VALIDATOR, Pro
from ..validators import require_structure_when_working
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
        validators=[POSTAL_CODE_VALIDATOR],
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
        require_structure_when_working(self, cleaned_data)
        return cleaned_data
