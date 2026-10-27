import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from techpourtoutes.models import Beneficiary, LegalRepresentativeAuthorization


@pytest.mark.django_db
def test_a_new_authorization_is_pending_behind_its_own_unguessable_token(authorization):
    sister = Beneficiary(
        username="lou@example.com", email="lou@example.com", first_name="Lou", last_name="Petit"
    )
    sister.save()
    other = LegalRepresentativeAuthorization(
        beneficiary=sister,
        legal_representative_name="Marie Petit",
        legal_representative_email="marie.petit@example.com",
    )
    other.save()

    assert authorization.status == LegalRepresentativeAuthorization.Status.PENDING
    assert len(authorization.token) >= 43
    assert authorization.token != other.token


@pytest.mark.django_db
@override_settings(SITE_URL="https://example.test")
def test_url_points_at_the_signing_form(authorization):
    assert authorization.url == f"https://example.test/autorisation/{authorization.token}/signer/"


@pytest.mark.django_db
def test_a_beneficiary_has_a_single_authorization(authorization, beneficiary):
    with pytest.raises(ValidationError):
        LegalRepresentativeAuthorization(
            beneficiary=beneficiary,
            legal_representative_name="Paul Petit",
            legal_representative_email="paul.petit@example.com",
        ).save()
