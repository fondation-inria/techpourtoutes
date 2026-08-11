from django import forms
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField


class BeneficiaryMentoringSignUpForm(forms.Form):
    legal_representative_name = forms.CharField(label=_("Nom d'une personne responsable légale*"))
    legal_representative_email = forms.EmailField(
        label=_("Adresse mail de la personne responsable légale*"),
        error_messages={"invalid": _("Saisis une adresse mail valide.")},
    )
    phone = PhoneNumberField(region="FR", label=_("Ton numéro de téléphone*"))
