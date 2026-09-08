from django import forms
from django.utils.translation import gettext_lazy as _

from ..fields import EmailField


class LoginRequestForm(forms.Form):
    email = EmailField(label=_("Adresse mail"))
