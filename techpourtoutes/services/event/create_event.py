from techpourtoutes.mailers import ConsortiumMailer, ProMailer
from techpourtoutes.models import Event

from ..base import BaseService


class CreateEvent(BaseService):
    """Writes the event the funnel collected, then tells its author and the moderation team.

    It lands as `PENDING`: nothing is published until someone validates it.
    """

    def perform(self, *, pro, forms):
        self.event = Event(created_by=pro)
        self.event.fill_from(forms)
        self.event.save()
        ProMailer.event_submitted(event=self.event)
        ConsortiumMailer.event_submitted(event=self.event)
