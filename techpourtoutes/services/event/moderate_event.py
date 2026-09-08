from techpourtoutes.mailers import ProMailer
from techpourtoutes.models import Event

from ..base import BaseService

_MAILER_BY_STATUS = {
    Event.Status.APPROVED: ProMailer.event_approved,
    Event.Status.REJECTED: ProMailer.event_rejected,
}


class ModerateEvent(BaseService):
    """Applies the moderator's decision and tells its author, carrying along whatever comment
    she attached. What the decision may not do — approving an ungeocoded event — is refused by
    the admin form that submits it, before the decision ever gets here."""

    def perform(self, *, event, status, comment=""):
        event.status = status
        event.save()
        _MAILER_BY_STATUS[status](event=event, comment=comment)
