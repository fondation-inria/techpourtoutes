from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import Pro, WorkshopRequest
from ..mixins import MissingRecordMixin
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


class WorkshopForm(MissingRecordMixin, BaseEngagementForm):
    pro_fields = ("job_title", "postal_code")
    pro_constants = {"professional_situation": Pro.ProfessionalSituation.WORKING}

    structure_uai = forms.CharField(widget=forms.HiddenInput, required=False)
    school_label = forms.CharField(label=_("Votre établissement*"))
    postal_code = forms.CharField(widget=forms.HiddenInput, required=False)
    school_not_found = forms.BooleanField(widget=forms.HiddenInput, required=False)
    job_title = forms.ChoiceField(label=_("Votre fonction*"), choices=FONCTION_CHOICES)
    remark = forms.CharField(label=_("Remarque"), required=False, widget=forms.Textarea)
    ateliers = forms.MultipleChoiceField(
        label=_("Atelier demandé*"),
        choices=WorkshopRequest.Type.choices,
        widget=forms.CheckboxSelectMultiple,
    )

    def clean(self):
        """Outside the fallback, the name must come from the autocomplete — hence its UAI."""
        cleaned_data = super().clean()
        if not self.school_not_found and not cleaned_data.get("structure_uai"):
            self.add_error("school_label", _("Sélectionnez un établissement dans la liste."))
        return cleaned_data

    def save(self, commit=True):
        pro = super().save(commit=False)
        pro.structure_name = self.cleaned_data["school_label"]
        if commit:
            pro.save()
        return pro
