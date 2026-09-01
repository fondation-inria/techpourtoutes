from techpourtoutes.mailers import ConsortiumMailer, ProMailer
from techpourtoutes.models import Event

from ..base import BaseService


class CreateEvent(BaseService):
    """Writes the event the funnel collected, then tells its author and the moderation team.

    It lands as `PENDING`: nothing is published until someone validates it.
    """

    def perform(self, *, pro, forms):
        subcategory_form, details_form, location_form = forms
        self.event = Event(
            created_by=pro,
            subcategory=subcategory_form.resolved_subcategory,
            **details_form.cleaned_data,
            **self._location(location_form),
        )
        self.event.save()
        ProMailer.event_submitted(event=self.event)
        ConsortiumMailer.new_event(event=self.event)

    def _location(self, location_form):
        """`address_api_down` says how the address was obtained, not what to store."""
        return {
            field: value
            for field, value in location_form.cleaned_data.items()
            if field != "address_api_down"
        }
