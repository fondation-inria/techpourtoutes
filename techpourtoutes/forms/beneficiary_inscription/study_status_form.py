from django import forms
from django.db import models
from django.utils.translation import gettext_lazy as _


class StudyStatus(models.TextChoices):
    HIGH_SCHOOL = "high_school", _("Je suis au collège ou au lycée")
    HIGHER_EDUCATION = "higher_education", _("Je fais des études supérieures")
    FINISHED = "finished", _("J'ai terminé mes études")
    RESUMING = "resuming", _("Je veux reprendre mes études")


class BeneficiaryStudyStatusForm(forms.Form):
    study_status = forms.ChoiceField(
        choices=StudyStatus.choices, widget=forms.RadioSelect, label=""
    )
