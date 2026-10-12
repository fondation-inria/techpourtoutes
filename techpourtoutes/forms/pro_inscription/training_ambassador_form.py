from django import forms
from django.utils.translation import gettext_lazy as _

from techpourtoutes.utils.school_year import (
    current_school_year_end_date,
    current_school_year_start_date,
)

from ...models import Formation, School, TrainingExperience
from ..fields import PhoneNumberField
from ..mixins import TrainingExperienceFormMixin
from ..validators import FORMATION_LABEL_MAX_LENGTH, SCHOOL_LABEL_MAX_LENGTH


class ProTrainingAmbassadorForm(TrainingExperienceFormMixin, forms.Form):
    """The school must be one of the partners: unlike the formation, it has no free-text
    fallback, hence no `school_not_found` flag."""

    school_label = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
        max_length=SCHOOL_LABEL_MAX_LENGTH,
        label=_("Dans quel établissement étudiez-vous ?*"),
    )
    school_id = forms.CharField(widget=forms.HiddenInput, required=False)
    formation_label = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
        max_length=FORMATION_LABEL_MAX_LENGTH,
        label=_("Quelle est votre formation ?*"),
    )
    formation_id = forms.CharField(widget=forms.HiddenInput, required=False)
    formation_not_found = forms.BooleanField(widget=forms.HiddenInput, required=False)
    phone = PhoneNumberField(required=False, region="FR", label=_("Votre numéro de téléphone"))

    def clean(self):
        cleaned_data = super().clean()
        self.resolve_school(School.objects.training_ambassador())
        self.resolve_formation(Formation.objects.higher_ed())
        self.validate_free_text()
        return cleaned_data

    def save(self, pro):
        return TrainingExperience.objects.create(
            user=pro,
            school=self._school,
            formation=self._formation,
            out_of_scope_school_name=self.out_of_scope_school_name,
            out_of_scope_formation_name=self.out_of_scope_formation_name,
            start_date=current_school_year_start_date(),
            end_date=current_school_year_end_date(),
        )
