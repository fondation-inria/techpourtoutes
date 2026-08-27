from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import TrainingExperience
from ...utils.school_year import school_year_choices, school_year_dates
from ..validators import FORMATION_LABEL_MAX_LENGTH, SCHOOL_LABEL_MAX_LENGTH
from .base_training_experience_form import BaseTrainingExperienceForm, level_choices

_ESTABLISHMENT_LABEL = _("Dans quel établissement as-tu obtenu ce diplôme ?*")


class BeneficiaryLastDiplomaTrainingExperienceForm(BaseTrainingExperienceForm):
    """Training of those who finished or want to resume their studies: their last diploma.

    Since the level covers both secondary and higher education, the screen carries the hidden
    fields of both search components and activates only the one matching the chosen level.
    """

    period_label = forms.ChoiceField(
        label=_("En quelle année as-tu obtenu ton dernier diplôme ?*"),
        choices=[("", _("Sélectionner une option")), *school_year_choices(years_forward=0)],
    )
    level = forms.ChoiceField(
        label=_("Quel est le niveau de ton diplôme ?*"),
        choices=level_choices(TrainingExperience.LEVELS),
    )
    school_label = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
        max_length=SCHOOL_LABEL_MAX_LENGTH,
        label=_ESTABLISHMENT_LABEL,
    )
    school_id = forms.CharField(widget=forms.HiddenInput, required=False)
    formation_label = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
        max_length=FORMATION_LABEL_MAX_LENGTH,
        label=_("De quelle formation es-tu diplômée ?*"),
    )
    formation_id = forms.CharField(widget=forms.HiddenInput, required=False)

    def training_dates(self):
        return school_year_dates(self.cleaned_data["period_label"])
