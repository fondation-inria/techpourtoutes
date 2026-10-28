import re

import pytest
from playwright.sync_api import expect

# A disabled button explains itself in a tooltip: a mouse shows it on hover, a finger on tap,
# the keyboard on focus.

REASON = re.compile("Cet engagement est réservé aux professionnelles")


@pytest.fixture
def touch_page(browser):
    context = browser.new_context(has_touch=True, viewport={"width": 390, "height": 844})
    yield context.new_page()
    context.close()


def _open_internships_as(page, live_server, beneficiary):
    page.goto(f"{live_server.url}/se-connecter/token/{beneficiary.issue_login_token()}/")
    page.goto(f"{live_server.url}/coalition/accueillir-une-stagiaire/")


def _open_days_tooltip(page):
    button = page.get_by_role("button", name="Organiser des portes ouvertes")
    return button.locator("xpath=..").get_by_role("tooltip")


def test_a_disabled_button_explains_itself_on_hover(page, live_server, beneficiary):
    _open_internships_as(page, live_server, beneficiary)

    page.get_by_role("button", name="Organiser des portes ouvertes").hover(force=True)
    expect(_open_days_tooltip(page)).to_have_text(REASON)


def test_a_disabled_button_explains_itself_on_tap(touch_page, live_server, beneficiary):
    _open_internships_as(touch_page, live_server, beneficiary)

    touch_page.get_by_role("button", name="Organiser des portes ouvertes").tap(force=True)
    expect(_open_days_tooltip(touch_page)).to_have_text(REASON)

    touch_page.get_by_role("heading", name="Accueillir une stagiaire").tap()
    expect(_open_days_tooltip(touch_page)).to_have_count(0)


def test_a_disabled_button_explains_itself_to_the_keyboard(page, live_server, beneficiary):
    _open_internships_as(page, live_server, beneficiary)

    button = page.get_by_role("button", name="Organiser des portes ouvertes")
    button.focus()
    expect(button).to_be_focused()
    expect(button).to_be_disabled()
    expect(button).to_have_accessible_description(REASON)
    expect(_open_days_tooltip(page)).to_have_text(REASON)

    page.keyboard.press("Escape")
    expect(_open_days_tooltip(page)).to_have_count(0)
