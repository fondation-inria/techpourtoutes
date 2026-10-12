from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import Pro

# Offered alongside the engagements without being one: nothing about them is stored on the pro.
EVENTS = "events"
OTHER = "other"

ENGAGEMENT_CHOICES = [
    (Pro.Engagement.MENTOR, _("Je veux devenir mentor")),
    (Pro.Engagement.WORK_AMBASSADOR, _("Je veux parler de mon métier")),
    (Pro.Engagement.INTERNSHIPS, _("Je veux proposer des stages")),
    (EVENTS, _("Je veux proposer des événements")),
    (Pro.Engagement.TRAINING_AMBASSADOR, _("Je veux devenir ambassadrice étudiante")),
    (Pro.Engagement.MOBILIZE_STRUCTURE, _("Je veux mobiliser ma structure")),
    (Pro.Engagement.WORKSHOPS, _("Je veux organiser un atelier pour mes élèves")),
    (Pro.Engagement.SPONSOR, _("Je veux devenir mécène ou proposer des bourses")),
    (OTHER, _("Autre")),
]


class ProEngagementsForm(forms.Form):
    engagements = forms.MultipleChoiceField(
        label=_("Comment souhaitez-vous contribuer ?"),
        choices=ENGAGEMENT_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": _("Choisissez au moins un engagement.")},
    )
    message = forms.CharField(
        label=_("Un message à transmettre à notre équipe ? Des précisions à apporter ?*"),
        max_length=1000,
        required=False,
        widget=forms.Textarea,
    )

    def clean(self):
        cleaned_data = super().clean()
        if OTHER not in cleaned_data.get("engagements", []):
            cleaned_data["message"] = ""
        elif not cleaned_data.get("message") and "message" not in self.errors:
            self.add_error("message", _("Ce champ est obligatoire."))
        return cleaned_data
