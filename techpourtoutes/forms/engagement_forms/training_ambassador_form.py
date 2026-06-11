from django import forms
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from ...models import Pro, TrainingExperience
from ..validators import resolve_higher_ed_school
from .base_engagement_form import BaseEngagementForm


class TrainingAmbassadorForm(BaseEngagementForm):
    pro_fields = ("phone",)
    prefill_fields = ("phone",)
    pro_constants = {
        "professional_situation": Pro.ProfessionalSituation.STUDENT,
    }

    phone = PhoneNumberField(required=False, region="FR", label=_("Votre n° de téléphone"))
    higher_ed_school_id = forms.CharField(
        widget=forms.HiddenInput, label=_("Votre établissement*")
    )
    higher_ed_school_label = forms.CharField(widget=forms.HiddenInput, required=False)
    course = forms.CharField(label=_("Votre cursus/spécialité*"))

    def clean_higher_ed_school_id(self):
        pk = self.cleaned_data["higher_ed_school_id"]
        self._higher_ed_school = resolve_higher_ed_school(pk)
        return pk

    def after_save(self, pro):
        training_experience, _created = TrainingExperience.objects.update_or_create(
            pro=pro,
            higher_ed_school=self._higher_ed_school,
            defaults={"course": self.cleaned_data["course"]},
        )
        return training_experience
