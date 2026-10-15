from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import WorkshopRequest
from ..mixins import MissingRecordMixin

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

# Those who answer one of these ask for a workshop in a school they do not work at.
OUTSIDE_SCHOOL_JOBS = (
    "DRANE / DAN / IAN",
    "parent d'élèves",
    "je ne travaille pas dans un établissement",
)
# Works at the school, but in no function the list names.
OTHER_SCHOOL_MISSION = "Autre mission au sein d'un établissement"


class ProWorkshopRequestForm(MissingRecordMixin, forms.Form):
    # Its school, job and postal code are not those of the other screens of the funnel, whose
    # answers all land in the same place.
    prefix = "workshop"

    structure_uai = forms.CharField(widget=forms.HiddenInput, required=False)
    school_label = forms.CharField(
        label=_("Pour quel établissement souhaitez-vous organiser un atelier ?*")
    )
    postal_code = forms.CharField(widget=forms.HiddenInput, required=False)
    school_not_found = forms.BooleanField(widget=forms.HiddenInput, required=False)
    job_title = forms.ChoiceField(label=_("Quel est votre métier ?*"), choices=FONCTION_CHOICES)
    ateliers = forms.MultipleChoiceField(
        label=_("Atelier demandé*"),
        choices=WorkshopRequest.Type.choices,
        widget=forms.CheckboxSelectMultiple,
    )
    remark = forms.CharField(label=_("Remarque"), required=False, widget=forms.Textarea)

    def clean(self):
        """Outside the fallback, the name must come from the autocomplete — hence its UAI."""
        cleaned_data = super().clean()
        if not self.school_not_found and not cleaned_data.get("structure_uai"):
            self.add_error("school_label", _("Sélectionnez un établissement dans la liste."))
        return cleaned_data

    @property
    def works_at_school(self):
        return self.cleaned_data["job_title"] not in OUTSIDE_SCHOOL_JOBS
