from uuid import uuid4

from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import TrainingExperience
from ...utils.school_year import current_school_year_end_date, current_school_year_start_date
from ..mixins import TrainingExperienceFormMixin


def level_choices(levels):
    return [
        ("", _("Sélectionner une option")),
        *[(level.value, level.label) for level in levels],
    ]


class BaseTrainingExperienceForm(TrainingExperienceFormMixin, forms.Form):
    """Training declared at registration.

    Each subclass declares the levels it offers, the hidden fields fed by its establishment
    search component, and the school year the training belongs to.
    """

    def __init__(self, *args, **kwargs):
        self.dom_id = uuid4().hex
        kwargs.setdefault("auto_id", f"id_{self.dom_id}_%s")
        super().__init__(*args, **kwargs)
        # Les réponses accumulées voyagent à chaque requête : un niveau choisi dans l'autre
        # branche ne doit pas pré-remplir un select qui ne le propose pas.
        if self.initial.get("level") not in dict(self.fields["level"].choices):
            self.initial["level"] = ""

    def clean(self):
        cleaned_data = super().clean()
        self.resolve_establishment(cleaned_data.get("level"))
        return cleaned_data

    def save(self, beneficiary):
        start_date, end_date = self.training_dates()
        return self.save_training(
            TrainingExperience(user=beneficiary, start_date=start_date, end_date=end_date)
        )

    def training_dates(self):
        """An ongoing training belongs to the current school year."""
        return current_school_year_start_date(), current_school_year_end_date()
