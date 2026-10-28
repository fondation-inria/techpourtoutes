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
    (Pro.Engagement.MOBILIZE_STRUCTURE, _("Je veux engager ma structure")),
    (Pro.Engagement.WORKSHOPS, _("Je veux organiser un atelier pour mes élèves")),
    (Pro.Engagement.SPONSOR, _("Je veux devenir mécène ou proposer des bourses")),
    (OTHER, _("Autre")),
]

# The only engagement a training ambassador may take on besides her own, for now.
TRAINING_AMBASSADOR_COMPATIBLE = (Pro.Engagement.TRAINING_AMBASSADOR, EVENTS)


class ProEngagementsForm(forms.Form):
    # Shown on hover over the engagements locked by the ones checked.
    student_only_reason = _(
        "Si vous êtes étudiante, vous ne pouvez que proposer des événements ou être "
        "ambassadrice étudiante. Les autres formes d'engagement vous seront ouvertes "
        "prochainement."
    )
    training_ambassador_apart_reason = _(
        "L'ambassadorat étudiant n'est pour l'instant pas compatible avec les autres formes "
        "d'engagement."
    )

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
        engagements = cleaned_data.get("engagements", [])
        if Pro.Engagement.TRAINING_AMBASSADOR in engagements and (
            set(engagements) - set(TRAINING_AMBASSADOR_COMPATIBLE)
        ):
            self.add_error("engagements", self.training_ambassador_apart_reason)
        if OTHER not in engagements:
            cleaned_data["message"] = ""
        elif not cleaned_data.get("message") and "message" not in self.errors:
            self.add_error("message", _("Ce champ est obligatoire."))
        return cleaned_data
