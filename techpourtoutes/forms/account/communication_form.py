from django import forms
from django.utils.translation import gettext_lazy as _


class CommunicationForm(forms.Form):
    newsletter_consent = forms.BooleanField(
        label=_("Je veux recevoir ponctuellement des nouvelles de TechPourToutes"),
        required=False,
    )

    def __init__(self, *args, user=None, **kwargs):
        if user is not None:
            kwargs.setdefault("initial", {"newsletter_consent": user.brevo_sync_enabled})
        super().__init__(*args, **kwargs)

    def save(self, user):
        user.brevo_sync_enabled = self.cleaned_data["newsletter_consent"]
        user.save()
        return user
