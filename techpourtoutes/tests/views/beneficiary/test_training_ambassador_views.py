import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

NEW_URL = "/echanger-avec-une-etudiante/demande/"
CREATE_URL = "/echanger-avec-une-etudiante/demande/envoyer/"
REQUEST_SUBJECT = "Nouvelle demande pour parler à une ambassadrice"


@pytest.mark.django_db
def test_new_training_ambassador_request_labels_the_topic_with_its_question(client, beneficiary):
    client.force_login(beneficiary)

    response = client.get(NEW_URL)

    assert b'<label for="id_topic">Quels sont les sujets' in response.content
    assert b'maxlength="1000"' in response.content


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_training_ambassador_request_records_it_and_mails_the_topic(client, beneficiary):
    client.force_login(beneficiary)

    response = client.post(CREATE_URL, {"topic": "Parcoursup et la vie sur le campus"})

    assert response["Location"] == reverse("show_account")
    beneficiary.refresh_from_db()
    assert beneficiary.has_requested_training_ambassador
    [request_mail] = mail.outbox
    assert request_mail.subject == REQUEST_SUBJECT
    assert "Parcoursup et la vie sur le campus" in request_mail.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_training_ambassador_request_without_a_topic_records_nothing(client, beneficiary):
    client.force_login(beneficiary)

    response = client.post(CREATE_URL, {"topic": ""})

    assert response.status_code == 200
    beneficiary.refresh_from_db()
    assert not beneficiary.has_requested_training_ambassador
    assert mail.outbox == []


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_training_ambassador_request_for_an_account_without_birth_date(client, beneficiary):
    # An account imported from Faveod may carry none.
    beneficiary.birth_date = None
    beneficiary.save()
    client.force_login(beneficiary)

    client.post(CREATE_URL, {"topic": "Parcoursup"})

    beneficiary.refresh_from_db()
    assert beneficiary.has_requested_training_ambassador


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
@pytest.mark.parametrize(("method", "url"), [("get", NEW_URL), ("post", CREATE_URL)])
def test_a_second_training_ambassador_request_goes_back_to_the_account(
    client, beneficiary, method, url
):
    beneficiary.has_requested_training_ambassador = True
    beneficiary.save()
    client.force_login(beneficiary)

    response = getattr(client, method)(url, {"topic": "Parcoursup"})

    assert response["Location"] == reverse("show_account")
    assert mail.outbox == []
