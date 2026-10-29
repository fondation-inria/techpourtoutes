from django.utils.translation import gettext_lazy as _

from ...forms.pro_inscription import ProEngagementsForm
from ...models import Pro
from ..base import BaseService

_ALREADY_TAKEN_ON = _("Vous avez déjà pris cet engagement.")


class CheckProEngagementEligibility(BaseService):
    """Fails when `pro` may not take on `engagement`, with `refusal_reason` saying why. A
    sponsorship or a workshop can be given again and again; a training ambassador, for now, takes
    on no other engagement — events, which she may still propose, are none."""

    refusal_reason = None

    def perform(self, *, pro, engagement):
        if engagement in pro.engagements and engagement not in Pro.REPEATABLE_ENGAGEMENTS:
            self._refuse(_ALREADY_TAKEN_ON)
        if pro.is_training_ambassador:
            self._refuse(ProEngagementsForm.student_only_reason)
        if engagement == Pro.Engagement.TRAINING_AMBASSADOR and pro.engagements:
            self._refuse(ProEngagementsForm.training_ambassador_apart_reason)

    def _refuse(self, reason):
        self.refusal_reason = reason
        self.fail(str(reason))
