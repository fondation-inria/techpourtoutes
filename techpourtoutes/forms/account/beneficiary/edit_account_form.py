from django import forms
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from techpourtoutes.forms.validators import validate_birth_date
from techpourtoutes.validators import POSTAL_CODE_VALIDATOR


class BeneficiaryEditAccountForm(forms.Form):
    first_name = forms.CharField(label=_("Prénom*"))
    last_name = forms.CharField(label=_("Nom*"))
    email = forms.EmailField(label=_("Email*"))
    phone = PhoneNumberField(region="FR", label=_("Numéro de téléphone"), required=False)
    birth_date = forms.DateField(label=_("Date de naissance*"), validators=[validate_birth_date])
    postal_code = forms.CharField(
        label=_("Code postal"),
        required=False,
        validators=[POSTAL_CODE_VALIDATOR],
    )

    def __init__(self, *args, beneficiary=None, **kwargs):
        if beneficiary is not None:
            kwargs.setdefault(
                "initial",
                {
                    "first_name": beneficiary.first_name,
                    "last_name": beneficiary.last_name,
                    "email": beneficiary.email,
                    "phone": beneficiary.phone.as_national if beneficiary.phone else "",
                    "birth_date": beneficiary.birth_date,
                    "postal_code": beneficiary.postal_code,
                },
            )
        super().__init__(*args, **kwargs)
        self.fields["email"].disabled = True
        self.fields["email"].required = False

    def save(self, beneficiary):
        data = self.cleaned_data
        beneficiary.first_name = data["first_name"]
        beneficiary.last_name = data["last_name"]
        beneficiary.phone = data["phone"]
        beneficiary.birth_date = data["birth_date"]
        beneficiary.postal_code = data["postal_code"]
        beneficiary.save()
        return beneficiary
