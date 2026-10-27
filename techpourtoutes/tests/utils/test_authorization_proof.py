import pytest
from django.template.loader import render_to_string
from django.utils import timezone

from techpourtoutes.utils.authorization_proof import build_authorization_proof


@pytest.fixture
def signed_authorization(authorization):
    authorization.legal_representative_name = "Marie Dupont"
    authorization.relationship = "mother"
    authorization.signed_at = timezone.now()
    authorization.document = render_to_string(
        "legal_representative_authorization/document.txt",
        {"authorization": authorization, "beneficiary": authorization.beneficiary},
    )
    return authorization


@pytest.mark.django_db
def test_build_authorization_proof_renders_a_pdf(signed_authorization):
    assert build_authorization_proof(signed_authorization).startswith(b"%PDF")


@pytest.mark.django_db
def test_build_authorization_proof_survives_a_name_outside_the_font(signed_authorization):
    signed_authorization.legal_representative_name = "Łucja Ştefan"

    assert build_authorization_proof(signed_authorization).startswith(b"%PDF")


@pytest.mark.django_db
def test_build_authorization_proof_carries_the_logo(signed_authorization):
    assert b"/Subtype /Image" in build_authorization_proof(signed_authorization)
