from techpourtoutes.mailers import ConsortiumMailer, ProMailer
from techpourtoutes.models import Event

from ..base import BaseService


class CreateEvent(BaseService):
    """Writes the event the funnel collected, then tells its author and the moderation team.

    It lands as `PENDING`: nothing is published until someone validates it — unless its author
    is the one who would validate it, and it goes online as it is written.
    """

    def perform(self, *, pro, forms):
        self.event = Event(created_by=pro)
        self.event.fill_from(forms)
        if self._has_publishing_rights(pro):
            self.event.status = Event.Status.APPROVED
        self.event.save()
        self._notify()

    def _has_publishing_rights(self, pro):
        return (pro.has_perm("techpourtoutes.change_event") or pro.is_superuser) and (
            self.event.location_type == Event.LocationType.ONLINE
            or self.event.latitude is not None
        )

    def _notify(self):
        if self.event.status == Event.Status.APPROVED:
            ProMailer.event_approved(event=self.event)
            return
        ProMailer.event_submitted(event=self.event)
        ConsortiumMailer.event_submitted(event=self.event)
