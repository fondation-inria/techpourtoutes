from datetime import date

from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import TrainingExperience, school_year_choices
from ..models.training_experience import current_school_year_label
from .validators import resolve_higher_ed_school, resolve_school


class BeneficiaryTrainingExperienceForm(forms.Form):
    period_label = forms.ChoiceField(label=_("Année*"), choices=lambda: _period_label_choices())
    not_enrolled = forms.BooleanField(
        label=_("Je ne suis pas inscrite dans une formation."),
        required=False,
    )
    level = forms.ChoiceField(
        label=_("Niveau*"),
        choices=[("", _("Sélectionner une option")), *TrainingExperience.Level.choices],
    )
    course = forms.CharField(label=_("Filière*"))
    school_name = forms.CharField(widget=forms.HiddenInput, required=False)
    school_identifier = forms.CharField(widget=forms.HiddenInput, required=False)
    school_postal_code = forms.CharField(widget=forms.HiddenInput, required=False)
    higher_ed_school_id = forms.CharField(widget=forms.HiddenInput, required=False)
    higher_ed_school_label = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, experience=None, beneficiary=None, current_year=False, **kwargs):
        if experience is not None:
            kwargs.setdefault("initial", _initial_from_experience(experience))
        super().__init__(*args, **kwargs)
        self._experience = experience
        self._beneficiary = beneficiary or (experience.user if experience else None)
        self._current_year = current_year or (
            experience is not None and experience.is_current_school_year
        )
        if self._current_year:
            label = current_school_year_label()
            self.fields["period_label"].choices = [(label, label)]
            self.fields["period_label"].disabled = True
            self.initial.setdefault("period_label", label)
            if experience is None:
                self.fields["not_enrolled"].initial = True
        else:
            del self.fields["not_enrolled"]
            current_label = current_school_year_label()
            self.fields["period_label"].choices = [
                choice for choice in _period_label_choices() if choice[0] != current_label
            ]
        if self._current_year and self.data.get("not_enrolled"):
            self.fields["level"].required = False
            self.fields["course"].required = False

    def clean(self):
        cleaned_data = super().clean()
        period_label = cleaned_data.get("period_label")
        if period_label and self._has_duplicate_period_label(period_label):
            self.add_error("period_label", _("Vous avez déjà renseigné cette année."))

        if cleaned_data.get("not_enrolled"):
            self._school = None
            self._higher_ed_school = None
            return cleaned_data

        level = cleaned_data.get("level")
        if not level:
            return cleaned_data

        if level in TrainingExperience.SECONDARY_LEVELS:
            self._school = self._resolve(
                "school_identifier", cleaned_data.get("school_identifier"), resolve_school
            )
            self._higher_ed_school = None
        else:
            self._higher_ed_school = self._resolve(
                "higher_ed_school_id",
                cleaned_data.get("higher_ed_school_id"),
                resolve_higher_ed_school,
            )
            self._school = None
        return cleaned_data

    def _has_duplicate_period_label(self, period_label):
        if self._beneficiary is None:
            return False
        start_date = _dates_from_period_label(period_label)[0]
        duplicates = self._beneficiary.training_experiences.filter(start_date=start_date)
        if self._experience is not None:
            duplicates = duplicates.exclude(pk=self._experience.pk)
        return duplicates.exists()

    def _resolve(self, field, value, resolver):
        if not value:
            self.add_error(field, _("Sélectionnez un établissement valide."))
            return None
        try:
            return resolver(value)
        except forms.ValidationError as error:
            self.add_error(field, error)
            return None

    def save(self, experience):
        experience.start_date, experience.end_date = _dates_from_period_label(
            self.cleaned_data["period_label"]
        )
        experience.level = self.cleaned_data["level"]
        experience.course = self.cleaned_data["course"]
        experience.school = self._school
        experience.higher_ed_school = self._higher_ed_school
        experience.save()
        return experience


def _period_label_choices():
    return [("", _("Sélectionner une option")), *school_year_choices()]


def _dates_from_period_label(period_label):
    start_year, end_year = (int(year) for year in period_label.split("-"))
    return date(start_year, 9, 1), date(end_year, 8, 31)


def _initial_from_experience(experience):
    return {
        "period_label": experience.period_label,
        "level": experience.level,
        "course": experience.course,
        "school_name": experience.school.name if experience.school else "",
        "school_identifier": experience.school.identifier if experience.school else "",
        "school_postal_code": experience.school.postal_code if experience.school else "",
        "higher_ed_school_id": (
            str(experience.higher_ed_school_id) if experience.higher_ed_school_id else ""
        ),
        "higher_ed_school_label": (
            experience.higher_ed_school.display_label if experience.higher_ed_school else ""
        ),
    }
