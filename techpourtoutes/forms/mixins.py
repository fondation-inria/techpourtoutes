from django import forms

from ..models import TrainingExperience
from .validators import resolve_higher_ed_school, resolve_school


class TrainingExperienceFormMixin:
    """Resolves the establishment picked in the autocomplete and writes the training.

    The hidden fields fed by the search components, as well as the training dates, stay
    declared by the form using the mixin.
    """

    _school = None
    _higher_ed_school = None

    def resolve_establishment(self, level):
        """The level decides the table: secondary → School, higher ed → HigherEdSchool."""
        if level in TrainingExperience.SECONDARY_LEVELS:
            self._school = self._resolve("school_identifier", resolve_school)
        elif level in TrainingExperience.HIGHER_ED_LEVELS:
            self._higher_ed_school = self._resolve("higher_ed_school_id", resolve_higher_ed_school)

    def save_training(self, experience):
        experience.level = self.cleaned_data["level"]
        experience.course = self.cleaned_data["course"]
        experience.school = self._school
        experience.higher_ed_school = self._higher_ed_school
        experience.save()
        return experience

    def _resolve(self, field, resolver):
        try:
            return resolver(self.cleaned_data[field])
        except forms.ValidationError as error:
            self.add_error(field, error)
