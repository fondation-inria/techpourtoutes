from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import TrainingExperience
from ..validators import FORMATION_LABEL_MAX_LENGTH, SCHOOL_LABEL_MAX_LENGTH
from .base_training_experience_form import BaseTrainingExperienceForm, level_choices


class BeneficiaryHighSchoolTrainingExperienceForm(BaseTrainingExperienceForm):
    level = forms.ChoiceField(
        label=_("En quelle classe es-tu ?*"),
        choices=level_choices(TrainingExperience.SECONDARY_LEVELS),
    )
    school_label = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
        max_length=SCHOOL_LABEL_MAX_LENGTH,
        label=_("Dans quel établissement étudies-tu ?*"),
    )
    school_id = forms.CharField(widget=forms.HiddenInput, required=False)
    formation_label = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
        max_length=FORMATION_LABEL_MAX_LENGTH,
        label=_("Quelle est ta formation ?*"),
    )
    formation_id = forms.CharField(widget=forms.HiddenInput, required=False)
