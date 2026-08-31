from django.utils.translation import gettext_lazy as _

from ..models import TrainingExperience

SCHOOL_LABEL_MAX_LENGTH = TrainingExperience._meta.get_field("out_of_scope_school_name").max_length
FORMATION_LABEL_MAX_LENGTH = TrainingExperience._meta.get_field(
    "out_of_scope_formation_name"
).max_length


def require_structure_when_working(form, cleaned_data):
    """Structure name is mandatory for pros declaring themselves in employment."""
    if cleaned_data.get("professional_situation") == "working" and not cleaned_data.get(
        "structure_name"
    ):
        form.add_error("structure_name", _("Ce champ est obligatoire."))


def validate_selected_school(form, school):
    if school is None:
        form.add_error("school_id", _("Sélectionnez un établissement valide."))


def validate_selected_formation(form, formation):
    if formation is None:
        form.add_error("formation_id", _("Sélectionnez une formation valide."))
