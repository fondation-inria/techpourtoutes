from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

from techpourtoutes.models import LegalRepresentativeAuthorization

SIGN = (
    "techpourtoutes.views.legal_representative_authorization_views."
    "SignLegalRepresentativeAuthorization"
)
Status = LegalRepresentativeAuthorization.Status

VALID_DATA = {
    "legal_representative_name": "Marie Dupont",
    "relationship": "mother",
    "authorization_confirmed": "on",
    "terms_accepted": "on",
    "newsletter_consent": "on",
}


def _show_url(authorization):
    return reverse("show_legal_representative_authorization", args=[authorization.token])


def _edit_url(authorization):
    return reverse("edit_legal_representative_authorization", args=[authorization.token])


def _update_url(authorization):
    return reverse("update_legal_representative_authorization", args=[authorization.token])


def _signed():
    return MagicMock(success=True, failure=False, errors=[])


def _set_status(authorization, status):
    authorization.status = status
    authorization.save()


@pytest.mark.django_db
def test_edit_legal_representative_authorization_prefills_the_name_given_by_the_beneficiary(
    client, authorization
):
    response = client.get(_edit_url(authorization))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Jade Petit" in content
    assert 'value="Marie Petit"' in content


@pytest.mark.django_db
def test_edit_legal_representative_authorization_sends_a_signed_link_to_its_outcome(
    client, authorization
):
    _set_status(authorization, Status.SIGNED)

    response = client.get(_edit_url(authorization))

    assert response.status_code == 302
    assert response.url == _show_url(authorization)


@pytest.mark.parametrize(
    "url_name",
    [
        "show_legal_representative_authorization",
        "edit_legal_representative_authorization",
    ],
)
@pytest.mark.django_db
def test_a_link_no_longer_valid_says_so(client, url_name):
    response = client.get(reverse(url_name, args=["remplace-ou-inconnu"]), follow=True)

    assert response.status_code == 200
    assert "Ce lien n'est plus valide" in response.content.decode()


@pytest.mark.django_db
def test_show_legal_representative_authorization_thanks_once_signed(client, authorization):
    _set_status(authorization, Status.SIGNED)

    response = client.get(_show_url(authorization))

    assert response.status_code == 200
    assert "Merci, votre autorisation a bien été enregistrée" in response.content.decode()


@pytest.mark.django_db
def test_show_legal_representative_authorization_sends_a_pending_link_to_the_form(
    client, authorization
):
    response = client.get(_show_url(authorization))

    assert response.status_code == 302
    assert response.url == _edit_url(authorization)


@pytest.mark.django_db
def test_update_legal_representative_authorization_signs_with_the_ip_and_redirects(
    client, authorization
):
    with patch(SIGN, return_value=_signed()) as MockSign:
        response = client.post(
            _update_url(authorization), VALID_DATA, headers={"x-forwarded-for": "203.0.113.7"}
        )

    assert response.status_code == 302
    assert response.url == _show_url(authorization)
    MockSign.assert_called_once_with(
        authorization=authorization,
        legal_representative_name="Marie Dupont",
        relationship="mother",
        newsletter_consent=True,
        ip_address="203.0.113.7",
    )


@pytest.mark.django_db
def test_update_legal_representative_authorization_shows_the_errors_of_an_invalid_form(
    client, authorization
):
    with patch(SIGN) as MockSign:
        response = client.post(
            _update_url(authorization), {"legal_representative_name": "Marie Dupont"}
        )

    assert response.status_code == 200
    assert response.context["form"].errors
    MockSign.assert_not_called()
    # The form posts to its own anchor, so the page it comes back with opens on its errors.
    content = response.content.decode()
    assert f'action="{_update_url(authorization)}#autorisation"' in content
    assert 'id="autorisation"' in content


@pytest.mark.django_db
def test_update_legal_representative_authorization_ignores_a_link_no_longer_pending(
    client, authorization
):
    _set_status(authorization, Status.SIGNED)

    with patch(SIGN) as MockSign:
        response = client.post(_update_url(authorization), VALID_DATA)

    assert response.status_code == 302
    assert response.url == _show_url(authorization)
    MockSign.assert_not_called()


@pytest.mark.django_db
def test_update_legal_representative_authorization_refuses_a_get(client, authorization):
    response = client.get(_update_url(authorization))

    assert response.status_code == 405


@pytest.mark.django_db
def test_update_legal_representative_authorization_says_a_link_no_longer_valid(client):
    with patch(SIGN) as MockSign:
        response = client.post(
            reverse("update_legal_representative_authorization", args=["remplace"]),
            VALID_DATA,
            follow=True,
        )

    assert "Ce lien n'est plus valide" in response.content.decode()
    MockSign.assert_not_called()
