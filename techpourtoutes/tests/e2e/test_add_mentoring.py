import re

import pytest
from playwright.sync_api import expect

from techpourtoutes.models import Beneficiary
from techpourtoutes.utils.dates import adult_birth_date

# These tests drive a real browser to cover what the view tests cannot: an account imported
# without a birth date only learns it is talking to a minor client-side, as she picks the date.

_LEGAL_REPRESENTATIVE_NAME = 'input[name="legal_representative_name"]'
_LEGAL_REPRESENTATIVE_EMAIL = 'input[name="legal_representative_email"]'


@pytest.fixture
def signed_in_page(live_server, page, db):
    beneficiary = Beneficiary(
        username="oceane@example.com",
        first_name="Océane",
        last_name="Martin",
        email="oceane@example.com",
    )
    beneficiary.save()
    page.goto(f"{live_server.url}/se-connecter/token/{beneficiary.issue_login_token()}/")
    page.goto(f"{live_server.url}/devenir-mentoree/")
    return page


def _birth_date_for_age(age):
    cutoff = adult_birth_date()
    return cutoff.replace(year=cutoff.year + 18 - age).isoformat()


def test_the_legal_representative_fields_stay_hidden_until_a_birth_date_is_picked(signed_in_page):
    expect(signed_in_page.locator(_LEGAL_REPRESENTATIVE_EMAIL)).to_be_hidden()
    expect(signed_in_page.get_by_text("Comme tu es mineure")).to_be_hidden()


def test_picking_a_minor_birth_date_reveals_the_legal_representative_fields(signed_in_page):
    signed_in_page.fill('input[name="birth_date"]', _birth_date_for_age(16))

    expect(signed_in_page.locator(_LEGAL_REPRESENTATIVE_NAME)).to_be_visible()
    expect(signed_in_page.locator(_LEGAL_REPRESENTATIVE_EMAIL)).to_be_visible()
    expect(signed_in_page.get_by_text("Comme tu es mineure")).to_be_visible()


def test_picking_an_adult_birth_date_keeps_the_legal_representative_fields_hidden(signed_in_page):
    signed_in_page.fill('input[name="birth_date"]', _birth_date_for_age(20))

    expect(signed_in_page.locator(_LEGAL_REPRESENTATIVE_EMAIL)).to_be_hidden()
    expect(signed_in_page.get_by_text("nous avons besoin de ta date de naissance")).to_be_visible()


def test_correcting_a_minor_birth_date_to_an_adult_one_hides_the_fields_again(signed_in_page):
    signed_in_page.fill('input[name="birth_date"]', _birth_date_for_age(16))
    expect(signed_in_page.locator(_LEGAL_REPRESENTATIVE_EMAIL)).to_be_visible()

    signed_in_page.fill('input[name="birth_date"]', _birth_date_for_age(20))

    expect(signed_in_page.locator(_LEGAL_REPRESENTATIVE_EMAIL)).to_be_hidden()


def test_a_minor_signs_up_in_a_single_submit(signed_in_page):
    signed_in_page.fill('input[name="birth_date"]', _birth_date_for_age(16))
    signed_in_page.fill('input[name="phone"]', "0612345678")
    signed_in_page.fill(_LEGAL_REPRESENTATIVE_NAME, "Hedy Lamarr")
    signed_in_page.fill(_LEGAL_REPRESENTATIVE_EMAIL, "hedy@example.com")

    signed_in_page.get_by_role("button", name="Rejoindre le mentorat").click()

    expect(signed_in_page).to_have_url(re.compile(r"/mon-compte/$"))
    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.legal_representative_email == "hedy@example.com"
