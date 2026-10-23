from unittest.mock import patch

import pytest
from django.core import mail

from techpourtoutes.models import LegalRepresentativeAuthorization
from techpourtoutes.services.legal_representative_authorization.sign_authorization import (
    SignLegalRepresentativeAuthorization,
)

PROOF_TASK = (
    "techpourtoutes.services.legal_representative_authorization.sign_authorization."
    "send_legal_representative_authorization_proof_task"
)
NEWSLETTER_TASK = (
    "techpourtoutes.services.legal_representative_authorization.sign_authorization."
    "subscribe_legal_representative_to_newsletter_task"
)
SIGNED = (
    "techpourtoutes.services.legal_representative_authorization.sign_authorization."
    "legal_representative_authorization_signed"
)
Status = LegalRepresentativeAuthorization.Status


@pytest.fixture(autouse=True)
def signed_signal():
    """What a signature unlocks is none of these tests' business: nobody hears it."""
    with patch(SIGNED) as signal:
        yield signal


def _sign(authorization, **overrides):
    return SignLegalRepresentativeAuthorization(
        authorization=authorization,
        **{
            "legal_representative_name": "Marie Dupont",
            "relationship": "mother",
            "newsletter_consent": True,
            "ip_address": "203.0.113.7",
            **overrides,
        },
    )


@pytest.mark.django_db
def test_sign_records_the_proof(authorization):
    result = _sign(authorization)

    assert result.success is True
    authorization.refresh_from_db()
    assert authorization.status == Status.SIGNED
    assert authorization.signed_at is not None
    assert authorization.legal_representative_name == "Marie Dupont"
    assert authorization.relationship == "mother"
    assert authorization.newsletter_consent is True
    assert authorization.ip_address == "203.0.113.7"


@pytest.mark.django_db
def test_sign_keeps_the_text_signed(authorization):
    _sign(authorization)

    authorization.refresh_from_db()
    for statement in (
        "Jade Petit souhaite rejoindre le programme TechPourToutes",
        "Je confirme donner mon autorisation en tant que personne responsable légale.",
        "J'accepte la politique de gestion des données personnelles de TechPourToutes.",
        "Marie Dupont",
        "Mère",
        "marie.petit@example.com",
    ):
        assert statement in authorization.document


@pytest.mark.django_db
def test_sign_leaves_the_pdf_and_the_mails_to_a_task_once_committed(
    authorization, django_capture_on_commit_callbacks
):
    with patch(PROOF_TASK) as proof_task, patch(NEWSLETTER_TASK):
        with django_capture_on_commit_callbacks(execute=True):
            _sign(authorization)

    authorization.refresh_from_db()
    assert not authorization.proof_pdf
    assert mail.outbox == []
    proof_task.delay.assert_called_once_with(authorization_pk=str(authorization.pk))


@pytest.mark.django_db
def test_sign_subscribes_to_the_newsletter_once_committed_when_asked(
    authorization, django_capture_on_commit_callbacks
):
    with patch(PROOF_TASK), patch(NEWSLETTER_TASK) as newsletter_task:
        with django_capture_on_commit_callbacks(execute=True):
            _sign(authorization)

    newsletter_task.delay.assert_called_once_with(email="marie.petit@example.com")


@pytest.mark.django_db
def test_sign_leaves_the_newsletter_alone_when_not_asked(
    authorization, django_capture_on_commit_callbacks
):
    with patch(PROOF_TASK), patch(NEWSLETTER_TASK) as newsletter_task:
        with django_capture_on_commit_callbacks(execute=True):
            _sign(authorization, newsletter_consent=False)

    newsletter_task.delay.assert_not_called()


@pytest.mark.django_db
def test_sign_refuses_an_authorization_already_signed(authorization):
    authorization.status = Status.SIGNED
    authorization.save()

    result = _sign(authorization)

    assert result.failure is True
    assert result.errors == ["Ce lien n'est plus valide."]


@pytest.mark.django_db
def test_sign_refuses_a_request_replaced_meanwhile(authorization):
    LegalRepresentativeAuthorization.objects.filter(pk=authorization.pk).delete()

    result = _sign(authorization)

    assert result.errors == ["Ce lien n'est plus valide."]


@pytest.mark.django_db
def test_sign_announces_the_signature_once_committed(
    authorization, signed_signal, django_capture_on_commit_callbacks
):
    with patch(PROOF_TASK), patch(NEWSLETTER_TASK):
        with django_capture_on_commit_callbacks(execute=True):
            _sign(authorization)
            signed_signal.send.assert_not_called()

    signed_signal.send.assert_called_once_with(
        sender=LegalRepresentativeAuthorization, authorization=authorization
    )


@pytest.mark.django_db
def test_sign_announces_nothing_when_refused(
    authorization, signed_signal, django_capture_on_commit_callbacks
):
    authorization.status = Status.SIGNED
    authorization.save()

    with django_capture_on_commit_callbacks(execute=True):
        _sign(authorization)

    signed_signal.send.assert_not_called()
