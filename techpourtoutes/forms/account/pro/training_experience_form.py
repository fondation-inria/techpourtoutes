from django import forms
from django.utils.translation import gettext_lazy as _

from ....models import School, TrainingExperience
from ...mixins import TrainingExperienceFormMixin
from ...validators import resolve_school


class ProTrainingExperienceForm(TrainingExperienceFormMixin, forms.Form):
    school_label = forms.CharField(
        widget=forms.HiddenInput, required=False, label=_("Votre établissement*")
    )
    school_id = forms.CharField(widget=forms.HiddenInput)
    level = forms.ChoiceField(
        label=_("Niveau*"),
        choices=[
            ("", _("Sélectionner une option")),
            *[(level.value, level.label) for level in TrainingExperience.HIGHER_ED_LEVELS],
        ],
    )
    formation_label = forms.CharField(
        widget=forms.HiddenInput, required=False, label=_("Votre formation*")
    )
    formation_id = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, experience=None, **kwargs):
        if experience is not None:
            formation = experience.formation
            kwargs.setdefault(
                "initial",
                {
                    "school_id": str(experience.school_id),
                    "school_label": experience.school.display_label,
                    "level": experience.level,
                    "formation_id": str(formation.pk) if formation else "",
                    "formation_label": formation.name if formation else "",
                },
            )
        super().__init__(*args, **kwargs)

    def clean_school_id(self):
        school_id = self.cleaned_data["school_id"]
        self._school = resolve_school(school_id, School.objects.higher_ed())
        return school_id

    def clean(self):
        """The formation resolves here, once every field clean has settled the school."""
        cleaned_data = super().clean()
        self.resolve_formation()
        return cleaned_data

    def save(self, experience):
        return self.save_training(experience)
