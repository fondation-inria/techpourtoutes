from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import TrainingExperience
from ...utils.school_year import school_year_choices, school_year_dates
from .base_training_experience_form import BaseTrainingExperienceForm, level_choices

_ESTABLISHMENT_LABEL = _("Dans quel établissement as-tu obtenu ce diplôme ?*")


class BeneficiaryLastDiplomaTrainingExperienceForm(BaseTrainingExperienceForm):
    """Formation de celles qui ont fini ou veulent reprendre leurs études : leur dernier diplôme.

    Le niveau ouvrant sur le secondaire comme sur le supérieur, l'écran porte les champs cachés
    des deux composants de recherche et n'en active qu'un, celui qui correspond au niveau choisi.
    """

    period_label = forms.ChoiceField(
        label=_("En quelle année as-tu obtenu ton dernier diplôme ?*"),
        choices=[("", _("Sélectionner une option")), *school_year_choices(years_forward=0)],
    )
    level = forms.ChoiceField(
        label=_("Quel est le niveau de ton diplôme ?*"),
        choices=level_choices(TrainingExperience.Level),
    )
    school_name = forms.CharField(
        widget=forms.HiddenInput, required=False, label=_ESTABLISHMENT_LABEL
    )
    school_identifier = forms.CharField(widget=forms.HiddenInput, required=False)
    school_postal_code = forms.CharField(widget=forms.HiddenInput, required=False)
    higher_ed_school_id = forms.CharField(
        widget=forms.HiddenInput, required=False, label=_ESTABLISHMENT_LABEL
    )
    higher_ed_school_label = forms.CharField(widget=forms.HiddenInput, required=False)
    course = forms.CharField(max_length=255, label=_("De quelle filière es-tu diplômée ?*"))

    def training_dates(self):
        return school_year_dates(self.cleaned_data["period_label"])
