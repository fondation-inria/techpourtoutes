from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from ..models import HigherEdSchool


def require_structure_when_working(form, cleaned_data):
    """Structure name is mandatory for pros declaring themselves in employment."""
    if cleaned_data.get("professional_situation") == "working" and not cleaned_data.get(
        "structure_name"
    ):
        form.add_error("structure_name", _("Ce champ est obligatoire."))


def resolve_higher_ed_school(pk):
    """Resolve a higher-ed school by primary key, raising a form error if it is unknown."""
    try:
        return HigherEdSchool.objects.get(pk=pk)
    except HigherEdSchool.DoesNotExist, ValidationError, ValueError:
        raise forms.ValidationError(_("Sélectionnez un établissement valide."))
