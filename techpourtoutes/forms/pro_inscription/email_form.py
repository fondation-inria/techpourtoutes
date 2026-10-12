from django import forms
from django.utils.translation import gettext_lazy as _

from ..fields import EmailField


class ProEmailForm(forms.Form):
    email = EmailField(
        label=_("Votre adresse mail"),
        error_messages={"invalid": _("Saisissez une adresse mail valide.")},
    )
