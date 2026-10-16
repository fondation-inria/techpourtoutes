import pytest
from django.core import mail
from django.urls import reverse

CREATE_URL = "/rejoindre-les-makeuses/proposition/envoyer/"
PROJECT = {
    "project_name": "Robot trieur",
    "project_link": "https://example.com/robot",
    "project_description": "Un robot qui trie les déchets",
}


@pytest.mark.django_db
def test_create_makeuse_project_submission_mails_the_team_and_her(client, beneficiary):
    client.force_login(beneficiary)

    response = client.post(CREATE_URL, PROJECT)

    assert response["Location"] == reverse("show_account")
    team_mail, beneficiary_mail = mail.outbox
    assert team_mail.subject == "Nouvelle proposition de projet Makeuse : Robot trieur"
    assert "https://example.com/robot" in team_mail.body
    assert beneficiary_mail.to == [beneficiary.email]


@pytest.mark.django_db
def test_create_makeuse_project_submission_without_a_name_sends_nothing(client, beneficiary):
    client.force_login(beneficiary)

    response = client.post(CREATE_URL, PROJECT | {"project_name": ""})

    assert response.status_code == 200
    assert mail.outbox == []


@pytest.mark.django_db
def test_create_makeuse_project_submission_with_an_invalid_link_sends_nothing(client, beneficiary):
    client.force_login(beneficiary)

    response = client.post(CREATE_URL, PROJECT | {"project_link": "mon drive"})

    assert response.status_code == 200
    assert mail.outbox == []


@pytest.mark.django_db
def test_create_makeuse_project_submission_accepts_a_second_project(client, beneficiary):
    client.force_login(beneficiary)
    client.post(CREATE_URL, PROJECT)

    client.post(CREATE_URL, PROJECT | {"project_name": "Appli de covoiturage"})

    assert len(mail.outbox) == 4
