from django import forms
from django.utils.translation import gettext_lazy as _

from .additional_information_form import ProAdditionalInformationForm


class ProSponsorForm(ProAdditionalInformationForm):
    """A pro supporting the programme: whatever her profile lacks, and a message for the team if
    she wishes."""

    message = forms.CharField(
        label=_("Votre message"), max_length=1000, required=False, widget=forms.Textarea
    )
