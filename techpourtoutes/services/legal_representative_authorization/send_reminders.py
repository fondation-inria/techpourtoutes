from datetime import timedelta

from django.utils import timezone

from ...mailers import BeneficiaryMailer, LegalRepresentativeMailer
from ...models import LegalRepresentativeAuthorization
from ..base import BaseService

# Days after the request on which it is still unsigned. Run once a day, the service finds each
# request on those very days only, so it needs no record of what it already sent.
LEGAL_REPRESENTATIVE_REMINDER_DAYS = (7, 14, 21)
BENEFICIARY_REMINDER_DAYS = (14,)


class SendLegalRepresentativeAuthorizationReminders(BaseService):
    """Run daily: mails the request again to every legal representative who has not signed yet,
    and tells the beneficiaries still waiting after two weeks."""

    def perform(self):
        self.legal_representatives_reminded = 0
        for authorization in _pending_requested(LEGAL_REPRESENTATIVE_REMINDER_DAYS):
            LegalRepresentativeMailer.authorization_requested(authorization=authorization)
            self.legal_representatives_reminded += 1
        self.beneficiaries_reminded = 0
        for authorization in _pending_requested(BENEFICIARY_REMINDER_DAYS):
            BeneficiaryMailer.legal_representative_authorization_reminder(
                authorization=authorization
            )
            self.beneficiaries_reminded += 1


def _pending_requested(days_ago):
    today = timezone.localdate()
    return (
        LegalRepresentativeAuthorization.objects.pending()
        .select_related("beneficiary")
        .filter(created_at__date__in=[today - timedelta(days=days) for days in days_ago])
    )
