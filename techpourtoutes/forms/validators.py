from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from techpourtoutes.utils.dates import compute_age

from ..models import Formation, School


def require_structure_when_working(form, cleaned_data):
    """Structure name is mandatory for pros declaring themselves in employment."""
    if cleaned_data.get("professional_situation") == "working" and not cleaned_data.get(
        "structure_name"
    ):
        form.add_error("structure_name", _("Ce champ est obligatoire."))


def resolve_school(school_id, queryset=None):
    """Resolve a school by primary key, raising a form error if it is unknown."""
    schools = School.objects.all() if queryset is None else queryset
    try:
        return schools.get(pk=school_id)
    except School.DoesNotExist, ValidationError, ValueError:
        raise forms.ValidationError(_("Sélectionnez un établissement valide."))


def resolve_formation(formation_id, queryset=None):
    """Resolve a formation by primary key, raising a form error if it is unknown."""
    formations = Formation.objects.all() if queryset is None else queryset
    try:
        return formations.get(pk=formation_id)
    except Formation.DoesNotExist, ValidationError, ValueError:
        raise forms.ValidationError(_("Sélectionnez une formation valide."))


def validate_birth_date(birth_date):
    """Beneficiaries must be between 15 and 25 years old."""
    age = compute_age(birth_date=birth_date)
    if age < 15 or age > 25:
        raise forms.ValidationError(_("L'âge doit être compris entre 15 et 25 ans."))
