from django import forms
from django.utils.translation import gettext_lazy as _


class LoginRequestForm(forms.Form):
    email = forms.EmailField(label=_("Adresse mail"))
