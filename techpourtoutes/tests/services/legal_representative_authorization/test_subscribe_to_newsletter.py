from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.legal_representative_authorization.subscribe_to_newsletter import (
    SubscribeLegalRepresentativeToNewsletter,
)

UPSERT = (
    "techpourtoutes.services.legal_representative_authorization.subscribe_to_newsletter."
    "UpsertBrevoContact"
)


@pytest.mark.django_db
def test_subscribe_adds_the_email_to_the_legal_representatives_list(settings):
    settings.BREVO_LEGAL_REPRESENTATIVE_LIST_ID = 21

    with patch(UPSERT, return_value=MagicMock(failure=False)) as upsert:
        result = SubscribeLegalRepresentativeToNewsletter(email="marie.petit@example.com")

    assert result.success is True
    upsert.assert_called_once_with(list_id=21, attributes={"EMAIL": "marie.petit@example.com"})


@pytest.mark.django_db
def test_subscribe_does_nothing_without_a_list(settings):
    settings.BREVO_LEGAL_REPRESENTATIVE_LIST_ID = 0

    with patch(UPSERT) as upsert:
        SubscribeLegalRepresentativeToNewsletter(email="marie.petit@example.com")

    upsert.assert_not_called()


@pytest.mark.django_db
def test_subscribe_relays_a_brevo_failure(settings):
    settings.BREVO_LEGAL_REPRESENTATIVE_LIST_ID = 21
    failed = MagicMock(failure=True, errors=["Brevo indisponible"], error_kind=ErrorKind.TRANSIENT)

    with patch(UPSERT, return_value=failed):
        result = SubscribeLegalRepresentativeToNewsletter(email="marie.petit@example.com")

    assert result.errors == ["Brevo indisponible"]
    assert result.failed_with_transient_error is True
