from django import forms
from django.utils.translation import gettext_lazy as _


class VerificationCodeForm(forms.Form):
    code = forms.CharField(label=_("Code de vérification"), max_length=6)
