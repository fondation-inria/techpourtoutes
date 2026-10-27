from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from techpourtoutes.models import LegalRepresentativeAuthorization
from techpourtoutes.services.legal_representative_authorization.send_reminders import (
    SendLegalRepresentativeAuthorizationReminders,
)


def _requested_days_ago(authorization, days, **fields):
    LegalRepresentativeAuthorization.objects.filter(pk=authorization.pk).update(
        created_at=timezone.now() - timedelta(days=days), **fields
    )


@pytest.mark.parametrize(
    ("days", "legal_representatives_reminded", "beneficiaries_reminded"),
    [(6, 0, 0), (7, 1, 0), (8, 0, 0), (14, 1, 1), (21, 1, 0), (28, 0, 0)],
)
@pytest.mark.django_db
def test_send_reminders_mails_on_the_7th_14th_and_21st_day_and_tells_her_on_the_14th(
    authorization, days, legal_representatives_reminded, beneficiaries_reminded
):
    _requested_days_ago(authorization, days)

    result = SendLegalRepresentativeAuthorizationReminders()

    assert result.legal_representatives_reminded == legal_representatives_reminded
    assert result.beneficiaries_reminded == beneficiaries_reminded
    assert len(mail.outbox) == legal_representatives_reminded + beneficiaries_reminded


@pytest.mark.django_db
def test_send_reminders_mails_the_request_again_to_the_legal_representative(authorization):
    _requested_days_ago(authorization, 7)

    SendLegalRepresentativeAuthorizationReminders()

    assert mail.outbox[0].to == ["marie.petit@example.com"]
    assert authorization.url in mail.outbox[0].body


@pytest.mark.django_db
def test_send_reminders_tells_the_beneficiary(authorization):
    _requested_days_ago(authorization, 14)

    SendLegalRepresentativeAuthorizationReminders()

    assert "jade@example.com" in [message.to[0] for message in mail.outbox]


@pytest.mark.django_db
def test_send_reminders_skips_a_signed_authorization(authorization):
    _requested_days_ago(authorization, 14, status=LegalRepresentativeAuthorization.Status.SIGNED)

    result = SendLegalRepresentativeAuthorizationReminders()

    assert result.legal_representatives_reminded == 0
    assert mail.outbox == []
