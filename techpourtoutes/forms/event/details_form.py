from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y"]


class EventDetailsForm(forms.Form):
    organizer = forms.CharField(
        label=_("Nom de l'organisateur*"),
        help_text=_("Ce nom s'affichera sur la fiche de l'événement"),
    )
    title = forms.CharField(label=_("Nom de l'événement*"))
    description = forms.CharField(widget=forms.Textarea, label=_("Description de l'événement*"))
    start_date = forms.DateField(label=_("Date de début*"), input_formats=DATE_FORMATS)
    start_time = forms.TimeField(label=_("Heure de début*"))
    end_date = forms.DateField(label=_("Date de fin*"), input_formats=DATE_FORMATS)
    end_time = forms.TimeField(label=_("Heure de fin*"))

    def __init__(self, *args, event=None, **kwargs):
        if event is not None:
            kwargs.setdefault("initial", self._initial_from_event(event))
        super().__init__(*args, **kwargs)

    @property
    def event_fields(self):
        """Every answer this screen collects is a column of its own."""
        return self.cleaned_data

    def clean(self):
        """Mirrors the `event_ends_after_it_starts` constraint, so the error lands on a field
        rather than surfacing from `full_clean()` at save time. The "not already over" rule stays
        here alone: a check constraint cannot look at today's date."""
        cleaned_data = super().clean()
        start_date, end_date = cleaned_data.get("start_date"), cleaned_data.get("end_date")
        start_time, end_time = cleaned_data.get("start_time"), cleaned_data.get("end_time")
        if not (start_date and end_date):
            return cleaned_data
        if end_date < timezone.localdate():
            self.add_error("end_date", _("L'événement ne peut pas être déjà terminé."))
        elif end_date < start_date:
            self.add_error("end_date", _("La date de fin doit suivre la date de début."))
        elif end_date == start_date and start_time and end_time and end_time < start_time:
            self.add_error("end_time", _("L'heure de fin doit suivre l'heure de début."))
        return cleaned_data

    def _initial_from_event(self, event):
        """Dates and times as their inputs expect them, never localised: they travel through a
        hidden input before they come back here, and `{{ }}` would render them in French."""
        return {
            "organizer": event.organizer,
            "title": event.title,
            "description": event.description,
            "start_date": event.start_date.isoformat(),
            "start_time": event.start_time.strftime("%H:%M"),
            "end_date": event.end_date.isoformat(),
            "end_time": event.end_time.strftime("%H:%M"),
        }
