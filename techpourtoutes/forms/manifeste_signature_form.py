from django import forms
from django.utils.translation import gettext_lazy as _


class ManifesteSignatureForm(forms.Form):
    """Lightweight manifeste signature: collects identity + organisation, no account.

    The cleaned values are pushed to Brevo as a contact; nothing is written to the
    database, so there is no `save()`.
    """

    first_name = forms.CharField(label=_("Votre prénom*"))
    last_name = forms.CharField(label=_("Votre nom*"))
    email = forms.EmailField(
        label=_("Votre email*"),
        error_messages={"invalid": _("Saisissez une adresse mail valide.")},
    )
    structure_name = forms.CharField(label=_("Votre organisation*"))
