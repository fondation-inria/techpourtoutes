from django import forms
from django.utils.translation import gettext_lazy as _

from techpourtoutes.validators import POSTAL_CODE_VALIDATOR

from ...models import Pro
from ..fields import PhoneNumberField

# Those who answer one of these work in no structure to name.
WITHOUT_STRUCTURE = (Pro.StructureType.RETIRED, Pro.StructureType.JOBLESS)


class ProLastInformationForm(forms.Form):
    structure_type = forms.ChoiceField(
        label=_("Dans quel type de structure travaillez-vous ?*"),
        choices=[("", _("Sélectionner une option")), *Pro.StructureType.choices],
    )
    structure_name = forms.CharField(
        label=_("Quel est le nom de votre structure ?*"), required=False
    )
    job_title = forms.CharField(label=_("Quel est votre métier ?*"))
    phone = PhoneNumberField(region="FR", label=_("Votre numéro de téléphone*"))
    postal_code = forms.CharField(
        label=_("Votre code postal*"), validators=[POSTAL_CODE_VALIDATOR]
    )

    def __init__(self, *args, workshop_job_title=None, **kwargs):
        """The job given for a workshop request is shown, never changed: it is one of the
        functions Latitudes expects."""
        super().__init__(*args, **kwargs)
        if workshop_job_title:
            self.fields["job_title"].disabled = True
            self.fields["job_title"].initial = workshop_job_title

    def clean(self):
        cleaned_data = super().clean()
        structure_type = cleaned_data.get("structure_type")
        if structure_type in WITHOUT_STRUCTURE:
            cleaned_data["structure_name"] = ""
        elif structure_type and not cleaned_data.get("structure_name"):
            self.add_error("structure_name", _("Ce champ est obligatoire."))
        return cleaned_data
