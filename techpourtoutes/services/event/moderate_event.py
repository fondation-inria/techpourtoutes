from django.core.exceptions import ValidationError

from techpourtoutes.mailers import ProMailer
from techpourtoutes.models import Event

from ..base import BaseService

_MAILER_BY_STATUS = {
    Event.Status.APPROVED: ProMailer.event_approved,
    Event.Status.REJECTED: ProMailer.event_rejected,
}


class ModerateEvent(BaseService):
    """Applies the moderator's decision and tells its author, carrying along whatever comment
    she attached — a save may still refuse an ungeocoded event before either happens."""

    def perform(self, *, event, status, comment=""):
        event.status = status
        try:
            event.save()
        except ValidationError as error:
            self.fail(", ".join(error.messages))
        _MAILER_BY_STATUS[status](event=event, comment=comment)
