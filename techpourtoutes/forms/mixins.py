from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Formation, Level, School, TrainingExperience
from .validators import resolve_formation, resolve_school


def school_label_for(level, school):
    """The text the autocomplete displayed for this school, per the level's perimeter."""
    if school is None:
        return ""
    if level in TrainingExperience.SECONDARY_LEVELS:
        return school.location_label
    return school.display_label


class MissingRecordMixin:
    """The record the user is looking for is absent from the Onisep catalogue.

    Each flag turns its autocomplete into a free-text field: the id stops being submitted and
    the typed name becomes mandatory in its place. The two flags are independent — not finding
    the school says nothing about the formation, which is then searched catalogue-wide.
    The form declares the flags itself; a bare mixin cannot carry form fields.
    """

    _school = None
    _formation = None

    @property
    def school_not_found(self):
        return self.cleaned_data.get("school_not_found", False)

    @property
    def formation_not_found(self):
        return self.cleaned_data.get("formation_not_found", False)

    @property
    def has_missing_record(self):
        return self.school_not_found or self.formation_not_found

    def validate_free_text(self):
        if self.school_not_found and not self.cleaned_data.get("school_label"):
            self.add_error("school_label", _("Indiquez le nom de votre établissement."))
        if self.formation_not_found and not self.cleaned_data.get("formation_label"):
            self.add_error("formation_label", _("Indiquez le nom de votre formation."))

    def missing_record_report(self):
        level = self.cleaned_data.get("level", "")
        return {
            "level": Level(level).label if level else "",
            "school_label": self.cleaned_data.get("school_label", ""),
            "formation_label": self.cleaned_data.get("formation_label", ""),
            "school": self._school,
            "formation": self._formation,
        }


class TrainingExperienceFormMixin(MissingRecordMixin):
    """Resolves the establishment picked in the autocomplete and writes the training.
    The school is always resolved first : it decides the formations offered to the user.
    The hidden fields fed by the search components, as well as the training dates, stay
    declared by the form using the mixin.
    """

    def resolve_school(self, queryset):
        if self.school_not_found:
            return
        self._school = self._resolve_school(queryset)

    def resolve_school_for_level(self, level):
        if level in TrainingExperience.SECONDARY_LEVELS:
            self.resolve_school(School.objects.secondary())
        elif level in TrainingExperience.HIGHER_ED_LEVELS:
            self.resolve_school(School.objects.higher_ed())

    def resolve_formation(self):
        if self.formation_not_found:
            return
        if self.school_not_found:
            self._formation = self._resolve_formation(Formation.objects.all())
        elif self._school:
            self._formation = self._resolve_formation(Formation.objects.taught_at(self._school))

    def save_training(self, experience):
        experience.level = self.cleaned_data["level"]
        experience.formation = self._formation
        experience.school = self._school
        experience.save()
        return experience

    def _resolve_school(self, queryset):
        try:
            return resolve_school(self.cleaned_data["school_id"], queryset)
        except forms.ValidationError as error:
            self.add_error("school_id", error)

    def _resolve_formation(self, queryset):
        try:
            return resolve_formation(self.cleaned_data["formation_id"], queryset)
        except forms.ValidationError as error:
            self.add_error("formation_id", error)
