from django.utils.translation import gettext_lazy as _

from ..models import TrainingExperience

SCHOOL_LABEL_MAX_LENGTH = TrainingExperience._meta.get_field("out_of_scope_school_name").max_length
FORMATION_LABEL_MAX_LENGTH = TrainingExperience._meta.get_field(
    "out_of_scope_formation_name"
).max_length


def validate_selected_school(form, school):
    if school is None:
        form.add_error("school_id", _("Sélectionner un établissement valide."))


def validate_selected_formation(form, formation):
    if formation is None:
        form.add_error("formation_id", _("Sélectionner une formation valide."))
