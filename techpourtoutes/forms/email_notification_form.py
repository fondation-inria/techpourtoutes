from django import forms
from django.utils.translation import gettext_lazy as _


class EmailNotificationForm(forms.Form):
    """Collects an email to notify when an upcoming feature launches."""

    email = forms.EmailField(
        label=_("Ton adresse mail"),
        error_messages={"invalid": _("Saisis une adresse mail valide.")},
    )
