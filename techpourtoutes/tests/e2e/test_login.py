import re

import pytest
from django.core import mail
from playwright.sync_api import expect

# These tests drive a real browser through the passwordless login flow: request a code by
# email, read it back from the outbox (there's no UI shortcut to it), then submit it.


@pytest.fixture
def login_url(live_server):
    return f"{live_server.url}/se-connecter/"


def test_login_with_valid_code_signs_the_pro_in(page, login_url, pro):
    _request_code(page, login_url, pro.email)

    page.fill('input[name="code"]', _last_code_sent())
    page.get_by_role("button", name="Continuer").click()

    expect(page).to_have_url(re.compile(r"/mon-compte/$"))
    expect(page.get_by_text(f"Bienvenue sur le compte {pro.email}")).to_be_visible()


def test_login_with_invalid_code_shows_an_error(page, login_url, pro):
    _request_code(page, login_url, pro.email)

    page.fill('input[name="code"]', "000000")
    page.get_by_role("button", name="Continuer").click()

    expect(page.get_by_text("Code invalide ou expiré.")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/se-connecter/code/$"))


def _request_code(page, login_url, email):
    page.goto(login_url)
    page.fill('input[name="email"]', email)
    page.get_by_role("button", name="Continuer").click()


def _last_code_sent():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)
