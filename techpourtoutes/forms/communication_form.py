from django import forms
from django.utils.translation import gettext_lazy as _


class CommunicationForm(forms.Form):
    newsletter_consent = forms.BooleanField(
        label=_("Je veux recevoir ponctuellement des nouvelles de TechPourToutes"),
        required=False,
    )

    def __init__(self, *args, pro=None, **kwargs):
        if pro is not None:
            kwargs.setdefault("initial", {"newsletter_consent": pro.brevo_sync_enabled})
        super().__init__(*args, **kwargs)

    def save(self, pro):
        pro.brevo_sync_enabled = self.cleaned_data["newsletter_consent"]
        pro.save()
        return pro
