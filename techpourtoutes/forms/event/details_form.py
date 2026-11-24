from django import forms
from django.core.files.storage import storages
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from ...utils.time_zones import TimeZone, wall_clock_furthest_behind, wall_clock_in
from ..fields import UploadedImageKeyField

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y"]

# What `create_event_image_upload` allows the browser send to the bucket.
IMAGE_PREFIX = "events"
IMAGE_CONTENT_TYPES = ("image/jpeg", "image/png", "image/webp")
IMAGE_SOURCE_MAX_SIZE = 30 * 1024 * 1024  # 30 Mo : what the user may pick, before any shrinking
IMAGE_MAX_SIZE = 2 * 1024 * 1024  # 2Mo : the limit after the browser shrinks the image


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
    choose_time_zone = forms.BooleanField(required=False, label=_("Choisir le fuseau horaire"))
    # Left unticked, the event gets its default zone: Paris, or the one of its address.
    time_zone = forms.ChoiceField(
        required=False,
        choices=[
            ("", _("Sélectionner une option")),
            *(
                (value, capfirst(label))
                for value, label in TimeZone.choices
                if value != TimeZone.PARIS
            ),
        ],
        label=_("Fuseau horaire*"),
    )
    image = UploadedImageKeyField(prefix=IMAGE_PREFIX)
    image_credit = forms.CharField(required=False, max_length=255, label=_("Crédit de l'image"))
    image_alt = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.Textarea,
        label=_("Alternative textuelle"),
        help_text=_(
            "Votre image est porteuse de sens ? Indiquez aux lecteurs d'écran son contenu"
        ),
    )
    image_accept = ",".join(IMAGE_CONTENT_TYPES)
    image_source_max_size = IMAGE_SOURCE_MAX_SIZE

    def __init__(self, *args, event=None, **kwargs):
        if event is not None:
            kwargs.setdefault("initial", self._initial_from_event(event))
        super().__init__(*args, **kwargs)

    @property
    def event_fields(self):
        """Every answer this screen collects is a column of its own, but whether she ticked the
        box: that is read back off the time zone."""
        return {
            field: value
            for field, value in self.cleaned_data.items()
            if field != "choose_time_zone"
        }

    @property
    def image_url(self):
        key = self["image"].value()
        return storages["public"].url(key) if key else ""

    def clean_image_credit(self):
        return self._only_with_an_image("image_credit")

    def clean_image_alt(self):
        return self._only_with_an_image("image_alt")

    def _only_with_an_image(self, field):
        """Without a visual, there is nothing to credit nor to describe."""
        return self.cleaned_data[field] if self.cleaned_data.get("image") else ""

    def clean(self):
        """Mirrors the `event_ends_after_it_starts` constraint, so the error lands on a field
        rather than surfacing from `full_clean()` at save time. The "not already over" rule stays
        here alone: a check constraint cannot look at today's date."""
        cleaned_data = super().clean()
        self._clean_time_zone(cleaned_data)
        start_date, end_date = cleaned_data.get("start_date"), cleaned_data.get("end_date")
        start_time, end_time = cleaned_data.get("start_time"), cleaned_data.get("end_time")
        if not (start_date and end_date):
            return cleaned_data
        now = self._wall_clock(cleaned_data)
        if end_date < now.date():
            self.add_error("end_date", _("L'événement ne peut pas être déjà terminé."))
        elif end_date == now.date() and end_time and end_time < now.time():
            self.add_error("end_time", _("L'événement ne peut pas être déjà terminé."))
        elif end_date < start_date:
            self.add_error("end_date", _("La date de fin doit suivre la date de début."))
        elif end_date == start_date and start_time and end_time and end_time < start_time:
            self.add_error("end_time", _("L'heure de fin doit suivre l'heure de début."))
        return cleaned_data

    def _clean_time_zone(self, cleaned_data):
        """Paris stands for "not chosen": `Event.clean` swaps it for the event's default."""
        if not cleaned_data.get("choose_time_zone"):
            cleaned_data["time_zone"] = TimeZone.PARIS
        elif not cleaned_data.get("time_zone"):
            self.add_error("time_zone", _("Choisissez le fuseau horaire de l'événement."))

    def _wall_clock(self, cleaned_data):
        """Left unticked, the zone is not known yet — a physical event takes the one of its
        postal code, given on the next screen — so only what is over in every zone is refused."""
        if cleaned_data.get("choose_time_zone") and cleaned_data.get("time_zone"):
            return wall_clock_in(cleaned_data["time_zone"])
        return wall_clock_furthest_behind()

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
            "choose_time_zone": "on" if self._chose_time_zone(event) else "",
            "time_zone": event.time_zone if self._chose_time_zone(event) else "",
            "image": event.image.name,
            "image_alt": event.image_alt,
            "image_credit": event.image_credit,
        }

    def _chose_time_zone(self, event):
        return event.time_zone != event.default_time_zone
