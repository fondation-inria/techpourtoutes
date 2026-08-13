from uuid import uuid4

from django import forms
from django.utils.translation import gettext_lazy as _

from techpourtoutes.utils.school_year import (
    current_school_year_label,
    school_year_choices,
    school_year_dates,
)

from ....models import TrainingExperience
from ...mixins import TrainingExperienceFormMixin


class BeneficiaryTrainingExperienceForm(TrainingExperienceFormMixin, forms.Form):
    period_label = forms.ChoiceField(label=_("Année*"))
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
        self.current_year = current_year or (
            experience is not None and experience.is_current_school_year
        )
        self.dom_id = self._build_dom_id(experience, self.current_year)
        if experience is not None:
            kwargs.setdefault("initial", self._initial_from_experience(experience))
        kwargs.setdefault("auto_id", f"id_{self.dom_id}_%s")
        super().__init__(*args, **kwargs)
        self._experience = experience
        self._beneficiary = beneficiary or (experience.user if experience else None)
        self._setup_period_label()
        self._setup_not_enrolled()

    def clean(self):
        cleaned_data = super().clean()
        period_label = cleaned_data.get("period_label")
        if period_label and self._has_duplicate_period_label(period_label):
            self.add_error("period_label", _("Vous avez déjà renseigné cette année."))
        if not cleaned_data.get("not_enrolled"):
            self.resolve_establishment(cleaned_data.get("level"))
        return cleaned_data

    def save(self, experience):
        experience.start_date, experience.end_date = school_year_dates(
            self.cleaned_data["period_label"]
        )
        return self.save_training(experience)

    def _setup_period_label(self):
        """The current school year owns a dedicated locked form; other years exclude it."""
        current_label = current_school_year_label()
        field = self.fields["period_label"]
        if self.current_year:
            field.choices = [(current_label, current_label)]
            field.disabled = True
            self.initial.setdefault("period_label", current_label)
        else:
            field.choices = [
                ("", _("Sélectionner une option")),
                *[choice for choice in school_year_choices() if choice[0] != current_label],
            ]

    def _setup_not_enrolled(self):
        """Only the current year can be declared without a training, which then needs no detail."""
        if not self.current_year:
            del self.fields["not_enrolled"]
            return
        self.fields["not_enrolled"].initial = self._experience is None
        if self.data.get("not_enrolled"):
            self.fields["level"].required = False
            self.fields["course"].required = False

    def _has_duplicate_period_label(self, period_label):
        if self._beneficiary is None:
            return False
        start_date = school_year_dates(period_label)[0]
        duplicates = self._beneficiary.training_experiences.filter(start_date=start_date)
        if self._experience is not None:
            duplicates = duplicates.exclude(pk=self._experience.pk)
        return duplicates.exists()

    @staticmethod
    def _build_dom_id(experience, current_year):
        """Namespaces element ids so several open forms never collide on the account page."""
        if experience is not None:
            return str(experience.pk)
        return "current-year" if current_year else uuid4().hex

    @staticmethod
    def _initial_from_experience(experience):
        school = experience.school
        higher_ed_school = experience.higher_ed_school
        return {
            "period_label": experience.period_label,
            "level": experience.level,
            "course": experience.course,
            "school_name": school.name if school else "",
            "school_identifier": school.identifier if school else "",
            "school_postal_code": school.postal_code if school else "",
            "higher_ed_school_id": str(higher_ed_school.pk) if higher_ed_school else "",
            "higher_ed_school_label": higher_ed_school.display_label if higher_ed_school else "",
        }
