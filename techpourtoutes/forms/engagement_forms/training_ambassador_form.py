from django import forms
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from ...models import Pro
from .base_engagement_form import BaseEngagementForm


class TrainingAmbassadorForm(BaseEngagementForm):
    pro_fields = ("phone", "structure_name", "structure_id", "postal_code")
    prefill_fields = ("phone",)
    pro_constants = {
        "professional_situation": Pro.ProfessionalSituation.STUDENT,
        "job_title": "Étudiante",
    }

    phone = PhoneNumberField(required=False, region="FR", label=_("Votre n° de téléphone"))
    structure_id = forms.CharField(widget=forms.HiddenInput)
    structure_name = forms.CharField(label=_("Établissement*"))
    postal_code = forms.CharField(widget=forms.HiddenInput)
