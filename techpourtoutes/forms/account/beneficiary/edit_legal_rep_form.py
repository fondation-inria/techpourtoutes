from django import forms
from django.utils.translation import gettext_lazy as _


class BeneficiaryLegalRepEditForm(forms.Form):
    legal_representative_name = forms.CharField(label=_("Prénom Nom*"))
    legal_representative_email = forms.EmailField(label=_("Adresse mail*"))

    def __init__(self, *args, authorization=None, **kwargs):
        if authorization is not None:
            kwargs.setdefault(
                "initial",
                {
                    "legal_representative_name": authorization.legal_representative_name,
                    "legal_representative_email": authorization.legal_representative_email,
                },
            )
        super().__init__(*args, **kwargs)
