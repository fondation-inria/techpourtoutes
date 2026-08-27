from django import forms
from django.utils.translation import gettext_lazy as _

from ....models import Formation, School, TrainingExperience
from ...mixins import TrainingExperienceFormMixin
from ...validators import FORMATION_LABEL_MAX_LENGTH, SCHOOL_LABEL_MAX_LENGTH


class ProTrainingExperienceForm(TrainingExperienceFormMixin, forms.Form):
    school_label = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
        max_length=SCHOOL_LABEL_MAX_LENGTH,
        label=_("Votre établissement*"),
    )
    school_id = forms.CharField(widget=forms.HiddenInput, required=False)
    school_not_found = forms.BooleanField(widget=forms.HiddenInput, required=False)
    formation_not_found = forms.BooleanField(widget=forms.HiddenInput, required=False)
    level = forms.ChoiceField(
        label=_("Niveau*"),
        choices=[
            ("", _("Sélectionner une option")),
            *[(level.value, level.label) for level in TrainingExperience.HIGHER_ED_LEVELS],
        ],
    )
    formation_label = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
        max_length=FORMATION_LABEL_MAX_LENGTH,
        label=_("Votre formation*"),
    )
    formation_id = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, experience=None, **kwargs):
        if experience is not None:
            kwargs.setdefault("initial", self._initial_from_experience(experience))
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        self.resolve_school(School.objects.higher_ed())
        self.resolve_formation(Formation.objects.higher_ed())
        self.validate_free_text()
        return cleaned_data

    def save(self, experience):
        return self.save_training(experience)

    @staticmethod
    def _initial_from_experience(experience):
        school, formation = experience.school, experience.formation
        return {
            "school_id": str(school.pk) if school else "",
            "school_label": experience.school_label,
            "school_not_found": school is None,
            "level": experience.level,
            "formation_id": str(formation.pk) if formation else "",
            "formation_label": experience.formation_label,
            "formation_not_found": formation is None,
        }
