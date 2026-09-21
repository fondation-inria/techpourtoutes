from techpourtoutes.mailers import ConsortiumMailer, ProMailer
from techpourtoutes.models import Event
from techpourtoutes.tasks import send_event_updated_email_task

from ..base import BaseService


class UpdateEvent(BaseService):
    """Writes the funnel's answers back onto an event, then tells whoever was watching it.

    An event still awaiting validation has no audience yet — it was never published — so only
    the moderation team hears about it.
    """

    def perform(self, *, event, forms):
        event.fill_from(forms)
        event.save()
        ConsortiumMailer.event_updated(event=event)
        if event.status != Event.Status.APPROVED:
            return
        ProMailer.event_updated(event=event)
        for beneficiary_pk in event.saved_by.values_list("pk", flat=True):
            send_event_updated_email_task.delay(
                event_pk=str(event.pk), beneficiary_pk=str(beneficiary_pk)
            )
