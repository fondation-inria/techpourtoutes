from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import TrainingExperience
from .base_training_experience_form import BaseTrainingExperienceForm, level_choices


class BeneficiaryHighSchoolTrainingExperienceForm(BaseTrainingExperienceForm):
    level = forms.ChoiceField(
        label=_("En quelle classe es-tu ?*"),
        choices=level_choices(TrainingExperience.SECONDARY_LEVELS),
    )
    school_name = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
        label=_("Dans quel établissement étudies-tu ?*"),
    )
    school_identifier = forms.CharField(widget=forms.HiddenInput, required=False)
    school_postal_code = forms.CharField(widget=forms.HiddenInput, required=False)
    course = forms.CharField(max_length=255, label=_("Quel diplôme prépares-tu ?*"))
