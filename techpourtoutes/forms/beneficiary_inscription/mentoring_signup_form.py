from django import forms
from django.utils.translation import gettext_lazy as _

from ...validators import POSTAL_CODE_VALIDATOR
from ..fields import PhoneNumberField


class BeneficiaryMentoringSignUpForm(forms.Form):
    legal_representative_name = forms.CharField(
        required=False, label=_("Nom d'une personne responsable légale*")
    )
    legal_representative_email = forms.EmailField(
        required=False,
        label=_("Adresse mail de la personne responsable légale*"),
        error_messages={"invalid": _("Saisis une adresse mail valide.")},
    )
    phone = PhoneNumberField(region="FR", label=_("Ton numéro de téléphone*"))
    postal_code = forms.CharField(
        required=False, label=_("Ton code postal*"), validators=[POSTAL_CODE_VALIDATOR]
    )
