from django import forms
from django.utils.translation import gettext_lazy as _

from .validators import resolve_higher_ed_school


class TrainingExperienceForm(forms.Form):
    higher_ed_school_id = forms.CharField(
        widget=forms.HiddenInput, label=_("Votre établissement*")
    )
    higher_ed_school_label = forms.CharField(widget=forms.HiddenInput, required=False)
    course = forms.CharField(label=_("Votre cursus/spécialité*"))

    def __init__(self, *args, experience=None, **kwargs):
        if experience is not None:
            kwargs.setdefault(
                "initial",
                {
                    "higher_ed_school_id": str(experience.higher_ed_school_id),
                    "higher_ed_school_label": experience.higher_ed_school.display_label,
                    "course": experience.course,
                },
            )
        super().__init__(*args, **kwargs)

    def clean_higher_ed_school_id(self):
        pk = self.cleaned_data["higher_ed_school_id"]
        self._higher_ed_school = resolve_higher_ed_school(pk)
        return pk

    def save(self, experience):
        experience.higher_ed_school = self._higher_ed_school
        experience.course = self.cleaned_data["course"]
        experience.save()
        return experience
