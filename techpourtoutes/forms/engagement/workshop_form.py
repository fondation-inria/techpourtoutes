from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import Pro, WorkshopRequest
from .base_engagement_form import BaseEngagementForm

FONCTION_CHOICES = [
    ("", _("Sélectionner une option")),
    ("Enseignante", _("Enseignante")),
    ("Documentaliste", _("Documentaliste")),
    ("CPE", _("CPE")),
    ("Responsable établissement", _("Responsable établissement")),
    ("Référente mission EDD", _("Référente mission EDD")),
    ("DRANE / DAN / IAN", _("DRANE / DAN / IAN")),
    ("Autre mission au sein d'un établissement", _("Autre mission au sein d'un établissement")),
    ("parent d'élèves", _("Parent d'élève")),
    ("je ne travaille pas dans un établissement", _("Je ne travaille pas dans un établissement")),
]


class WorkshopForm(BaseEngagementForm):
    pro_fields = ("structure_name", "structure_id", "job_title", "postal_code")
    pro_constants = {"professional_situation": Pro.ProfessionalSituation.WORKING}

    structure_id = forms.CharField(widget=forms.HiddenInput)
    structure_name = forms.CharField(label=_("Votre établissement*"))
    postal_code = forms.CharField(widget=forms.HiddenInput)
    job_title = forms.ChoiceField(label=_("Votre fonction*"), choices=FONCTION_CHOICES)
    remark = forms.CharField(label=_("Remarque"), required=False, widget=forms.Textarea)
    ateliers = forms.MultipleChoiceField(
        label=_("Atelier demandé*"),
        choices=WorkshopRequest.Type.choices,
        widget=forms.CheckboxSelectMultiple,
    )
