from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from waffle.testutils import override_switch

NEW_URL = "/rejoindre-le-discord/"
CREATE_URL = "/rejoindre-le-discord/connexion/"
REDIRECT_URI = f"https://techpourtoutes.test{CREATE_URL}"
JOIN_SERVICE = "techpourtoutes.views.beneficiary.discord_views.JoinDiscordServer"

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("discord_settings")]


@pytest.fixture(autouse=True)
def site_url(settings):
    settings.SITE_URL = "https://techpourtoutes.test"


@pytest.fixture(autouse=True)
def discord_switch(db):
    with override_switch("discord", active=True):
        yield


@pytest.fixture
def signed_in(client, beneficiary):
    client.force_login(beneficiary)
    return client


def _start_authorization(client):
    """Goes through `new_discord_membership` and returns the state Discord would hand back."""
    location = client.get(NEW_URL)["Location"]
    return parse_qs(urlsplit(location).query)["state"][0]


def _messages(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


@pytest.mark.parametrize("url", [NEW_URL, CREATE_URL])
def test_discord_membership_routes_do_not_exist_while_the_switch_is_off(signed_in, url):
    with override_switch("discord", active=False):
        assert signed_in.get(url).status_code == 404


def test_new_discord_membership_sends_a_visitor_to_the_login_and_back(client):
    response = client.get(NEW_URL)

    assert response["Location"] == f"{reverse('login_request')}?next={NEW_URL}"


def test_new_discord_membership_turns_a_pro_away(client, pro):
    client.force_login(pro)

    response = client.get(NEW_URL)

    assert response["Location"] == reverse("show_account")


def test_new_discord_membership_asks_discord_to_let_us_add_her_to_the_server(signed_in):
    response = signed_in.get(NEW_URL)

    location = urlsplit(response["Location"])
    query = parse_qs(location.query)
    assert f"{location.scheme}://{location.netloc}{location.path}" == (
        "https://discord.com/oauth2/authorize"
    )
    assert query["client_id"] == ["client-id"]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["identify guilds.join"]
    assert query["redirect_uri"] == [REDIRECT_URI]
    assert query["state"] == [signed_in.session["discord_oauth_state"]]


def test_create_discord_membership_joins_the_server_and_opens_it(signed_in, beneficiary):
    state = _start_authorization(signed_in)

    with patch(JOIN_SERVICE) as join:
        join.return_value = MagicMock(failure=False)
        response = signed_in.get(CREATE_URL, {"code": "the-code", "state": state})

    join.assert_called_once_with(
        beneficiary=beneficiary, code="the-code", redirect_uri=REDIRECT_URI
    )
    assert response["Location"] == "https://discord.com/channels/42"


def test_create_discord_membership_relays_why_she_could_not_join(signed_in):
    state = _start_authorization(signed_in)

    with patch(JOIN_SERVICE) as join:
        join.return_value = MagicMock(failure=True, errors=["Discord est indisponible."])
        response = signed_in.get(CREATE_URL, {"code": "the-code", "state": state})

    assert response["Location"] == reverse("show_account")
    assert _messages(response) == ["Discord est indisponible."]


def test_create_discord_membership_rejects_a_state_it_did_not_issue(signed_in):
    _start_authorization(signed_in)

    with patch(JOIN_SERVICE) as join:
        response = signed_in.get(CREATE_URL, {"code": "the-code", "state": "forged"})

    join.assert_not_called()
    assert response["Location"] == reverse("show_account")


def test_create_discord_membership_accepts_a_state_only_once(signed_in):
    state = _start_authorization(signed_in)

    with patch(JOIN_SERVICE) as join:
        join.return_value = MagicMock(failure=False)
        signed_in.get(CREATE_URL, {"code": "the-code", "state": state})
        signed_in.get(CREATE_URL, {"code": "the-code", "state": state})

    join.assert_called_once()


def test_create_discord_membership_lets_her_decline_on_discord(signed_in):
    state = _start_authorization(signed_in)

    with patch(JOIN_SERVICE) as join:
        response = signed_in.get(CREATE_URL, {"error": "access_denied", "state": state})

    join.assert_not_called()
    assert response["Location"] == reverse("show_account")
