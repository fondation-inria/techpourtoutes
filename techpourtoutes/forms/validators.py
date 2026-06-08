from django.utils.translation import gettext_lazy as _


def require_structure_when_working(form, cleaned_data):
    """Structure name is mandatory for pros declaring themselves in employment."""
    if cleaned_data.get("professional_situation") == "working" and not cleaned_data.get(
        "structure_name"
    ):
        form.add_error("structure_name", _("Ce champ est obligatoire."))
