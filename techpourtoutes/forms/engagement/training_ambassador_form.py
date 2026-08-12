from django import forms
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from techpourtoutes.utils.school_year import (
    current_school_year_end_date,
    current_school_year_start_date,
)

from ...models import Pro, School, TrainingExperience
from ..mixins import TrainingExperienceFormMixin
from ..validators import resolve_school
from .base_engagement_form import BaseEngagementForm


class TrainingAmbassadorForm(TrainingExperienceFormMixin, BaseEngagementForm):
    pro_fields = ("phone",)
    prefill_fields = ("phone",)
    pro_constants = {
        "professional_situation": Pro.ProfessionalSituation.STUDENT,
    }

    phone = PhoneNumberField(required=False, region="FR", label=_("Votre n° de téléphone"))
    school_label = forms.CharField(
        widget=forms.HiddenInput, required=False, label=_("Votre établissement*")
    )
    school_id = forms.CharField(widget=forms.HiddenInput)
    formation_label = forms.CharField(
        widget=forms.HiddenInput, required=False, label=_("Votre formation*")
    )
    formation_id = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean_school_id(self):
        school_id = self.cleaned_data["school_id"]
        self._school = resolve_school(school_id, School.objects.training_ambassador())
        return school_id

    def clean(self):
        """The formation resolves here, once every field clean has settled the school."""
        cleaned_data = super().clean()
        self.resolve_formation()
        return cleaned_data

    def after_save(self, pro):
        training_experience, _created = TrainingExperience.objects.update_or_create(
            user=pro,
            school=self._school,
            defaults={
                "formation": self._formation,
                "start_date": current_school_year_start_date(),
                "end_date": current_school_year_end_date(),
            },
        )
        return training_experience
