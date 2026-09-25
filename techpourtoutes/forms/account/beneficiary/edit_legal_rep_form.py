from django import forms
from django.utils.translation import gettext_lazy as _


class BeneficiaryLegalRepEditForm(forms.Form):
    legal_representative_name = forms.CharField(label=_("Prénom Nom*"))
    legal_representative_email = forms.EmailField(label=_("Adresse mail*"))

    def __init__(self, *args, beneficiary=None, **kwargs):
        if beneficiary is not None:
            kwargs.setdefault(
                "initial",
                {
                    "legal_representative_name": beneficiary.legal_representative_name,
                    "legal_representative_email": beneficiary.legal_representative_email,
                },
            )
        super().__init__(*args, **kwargs)

    def save(self, beneficiary):
        data = self.cleaned_data
        beneficiary.legal_representative_name = data["legal_representative_name"]
        beneficiary.legal_representative_email = data["legal_representative_email"]
        beneficiary.save()
        return beneficiary
