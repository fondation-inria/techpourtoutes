from django import forms
from django.utils.translation import gettext_lazy as _

from ..fields import PhoneNumberField
from ..validators import validate_birth_date


class BeneficiaryMentoringSignUpForm(forms.Form):
    birth_date = forms.DateField(
        label=_("Ta date de naissance*"),
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        validators=[validate_birth_date],
    )
    legal_representative_name = forms.CharField(
        required=False, label=_("Nom d'une personne responsable légale*")
    )
    legal_representative_email = forms.EmailField(
        required=False,
        label=_("Adresse mail de la personne responsable légale*"),
        error_messages={"invalid": _("Saisis une adresse mail valide.")},
    )
    phone = PhoneNumberField(region="FR", label=_("Ton numéro de téléphone*"))

    def __init__(self, *args, needs_birth_date=False, **kwargs):
        super().__init__(*args, **kwargs)
        # The funnel already asked for it at the identity step: only an account imported
        # from Faveod reaches this form without one.
        if not needs_birth_date:
            del self.fields["birth_date"]
