from django import forms

from ..models import Formation, School, TrainingExperience
from .validators import resolve_formation, resolve_school


def school_label_for(level, school):
    """The text the autocomplete displayed for this school, per the level's perimeter."""
    if school is None:
        return ""
    if level in TrainingExperience.SECONDARY_LEVELS:
        return school.location_label
    return school.display_label


class TrainingExperienceFormMixin:
    """Resolves the establishment picked in the autocomplete and writes the training.
    The school is always resolved first : it decides the formations offered to the user.
    The hidden fields fed by the search components, as well as the training dates, stay
    declared by the form using the mixin.
    """

    _school = None
    _formation = None

    def resolve_school(self, level):
        """The level decides the table: secondary or higher ed."""
        if level in TrainingExperience.SECONDARY_LEVELS:
            self._school = self._resolve(School.objects.secondary())
        elif level in TrainingExperience.HIGHER_ED_LEVELS:
            self._school = self._resolve(School.objects.higher_ed())

    def resolve_formation(self):
        """The school decides the formations to offer."""
        if self._school:
            self._formation = self._resolve_formation()

    def save_training(self, experience):
        experience.level = self.cleaned_data["level"]
        experience.formation = self._formation
        experience.school = self._school
        experience.save()
        return experience

    def _resolve(self, queryset):
        try:
            return resolve_school(self.cleaned_data["school_id"], queryset)
        except forms.ValidationError as error:
            self.add_error("school_id", error)

    def _resolve_formation(self):
        try:
            return resolve_formation(
                self.cleaned_data["formation_id"], Formation.objects.taught_at(self._school)
            )
        except forms.ValidationError as error:
            self.add_error("formation_id", error)
