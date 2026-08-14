from django.utils.translation import gettext_lazy as _

from ...models import Formation, School, TrainingExperience
from ..validators import validate_selected_formation, validate_selected_school
from .missing_record_mixin import MissingRecordMixin


class TrainingExperienceFormMixin(MissingRecordMixin):
    """Resolves the establishment picked in the autocomplete and writes the training.
    The school is always resolved first : it decides the formations offered to the user.
    The hidden fields fed by the search components, as well as the training dates, stay
    declared by the form using the mixin.
    """

    _level = None

    def resolve_school(self, queryset):
        if self.school_not_found:
            return
        self._school = queryset.find(self.cleaned_data["school_id"])
        validate_selected_school(self, self._school)

    def resolve_school_for_level(self, level):
        self._level = level
        if level in TrainingExperience.SECONDARY_LEVELS:
            self.resolve_school(School.objects.secondary())
        elif level in TrainingExperience.HIGHER_ED_LEVELS:
            self.resolve_school(School.objects.higher_ed())

    def resolve_formation(self, formations=None):
        if self.formation_not_found:
            return
        if formations is None:
            formations = self._formations_for_level()
        if self.school_not_found:
            self._formation = self._picked_formation_in(formations)
        elif self._school:
            self._formation = self._picked_formation_in(formations.taught_at(self._school))

    def validate_free_text(self):
        """A record declared absent from the catalogue must be named in its place."""
        if self.school_not_found and not self.cleaned_data.get("school_label"):
            self.add_error("school_label", _("Indiquez le nom de votre établissement."))
        if self.formation_not_found and not self.cleaned_data.get("formation_label"):
            self.add_error("formation_label", _("Indiquez le nom de votre formation."))

    def save_training(self, experience):
        experience.level = self.cleaned_data["level"]
        experience.formation = self._formation
        experience.school = self._school
        experience.out_of_scope_school_name = self.out_of_scope_school_name
        experience.out_of_scope_formation_name = self.out_of_scope_formation_name
        experience.save()
        return experience

    @staticmethod
    def school_label_for(level, school):
        """The text the autocomplete displayed for this school, per the level's perimeter."""
        if school is None:
            return ""
        if level in TrainingExperience.SECONDARY_LEVELS:
            return school.location_label
        return school.display_label

    def _picked_formation_in(self, formations):
        formation = formations.find(self.cleaned_data["formation_id"])
        validate_selected_formation(self, formation)
        return formation

    def _formations_for_level(self):
        if self._level in TrainingExperience.SECONDARY_LEVELS:
            return Formation.objects.secondary()
        if self._level in TrainingExperience.HIGHER_ED_LEVELS:
            return Formation.objects.higher_ed()
        return Formation.objects.all()
