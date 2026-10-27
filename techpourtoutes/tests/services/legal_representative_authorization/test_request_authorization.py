import pytest
from django.core import mail

from techpourtoutes.models import LegalRepresentativeAuthorization
from techpourtoutes.services.legal_representative_authorization.request_authorization import (
    RequestLegalRepresentativeAuthorization,
)


def _request(beneficiary, email="marie.petit@example.com"):
    return RequestLegalRepresentativeAuthorization(
        beneficiary=beneficiary,
        legal_representative_name="Marie Petit",
        legal_representative_email=email,
    )


@pytest.mark.django_db
def test_request_mails_a_personal_link_to_the_legal_representative(beneficiary):
    result = _request(beneficiary)

    assert result.success is True
    authorization = beneficiary.legal_representative_authorization
    assert authorization.status == LegalRepresentativeAuthorization.Status.PENDING
    assert authorization.legal_representative_name == "Marie Petit"
    assert authorization.legal_representative_email == "marie.petit@example.com"
    assert mail.outbox[0].to == ["marie.petit@example.com"]
    assert authorization.url in mail.outbox[0].body


@pytest.mark.django_db
def test_request_replaces_the_pending_request_and_its_link(authorization, beneficiary):
    _request(beneficiary, email="paul.petit@example.com")

    replacement = LegalRepresentativeAuthorization.objects.get()
    assert replacement.legal_representative_email == "paul.petit@example.com"
    assert replacement.token != authorization.token
