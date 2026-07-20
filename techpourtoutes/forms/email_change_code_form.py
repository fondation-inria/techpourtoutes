from django import forms
from django.utils.translation import gettext_lazy as _


class EmailChangeCodeForm(forms.Form):
    code = forms.CharField(label=_("Code de vérification"), max_length=6)
