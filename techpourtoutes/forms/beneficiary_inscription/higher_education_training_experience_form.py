from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import TrainingExperience
from .base_training_experience_form import BaseTrainingExperienceForm, level_choices


class BeneficiaryHigherEducationTrainingExperienceForm(BaseTrainingExperienceForm):
    level = forms.ChoiceField(
        label=_("Quel est ton niveau d'études actuel ?*"),
        choices=level_choices(TrainingExperience.HIGHER_ED_LEVELS),
    )
    school_label = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
        label=_("Dans quel établissement étudies-tu ?*"),
    )
    school_id = forms.CharField(widget=forms.HiddenInput, required=False)
    formation_label = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
        label=_("Quelle est ta formation ?*"),
    )
    formation_id = forms.CharField(widget=forms.HiddenInput, required=False)
