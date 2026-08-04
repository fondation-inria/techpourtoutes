import pytest
from playwright.sync_api import expect
from waffle.testutils import override_switch

# These tests drive a real browser to cover what the view tests cannot: the client-side
# sessionStorage behaviour (survive reload, wipe on explicit exit) wired through Alpine + HTMX.


@pytest.fixture
def funnel_url(live_server):
    return f"{live_server.url}/inscription/"


@pytest.fixture
def beneficiary_mode():
    with override_switch("beneficiary_mode", active=True):
        yield


def _complete_email_step(page, email="oceane@example.com"):
    expect(page.locator('input[name="step"]:not([value="back"])')).to_have_value("email")
    page.fill('input[name="email"]', email)
    page.get_by_role("button", name="Continuer").click()
    expect(page.locator('input[name="step"]:not([value="back"])')).to_have_value("identity")


def _complete_identity_step(page, birth_date="2005-01-01"):
    page.fill('input[name="first_name"]', "Océane")
    page.fill('input[name="last_name"]', "Durand")
    page.fill('input[name="birth_date"]', birth_date)
    page.locator('input[name="age_eligibility_accepted"]').check(force=True)
    page.locator('input[name="terms_accepted"]').check(force=True)
    page.get_by_role("button", name="Continuer").click()


def test_reload_keeps_progress(page, funnel_url, beneficiary_mode):
    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    expect(page.locator('input[name="step"]:not([value="back"])')).to_have_value("study_status")

    page.reload()

    # The stored answers are re-hydrated from sessionStorage and the funnel resumes where it was.
    expect(page.locator('input[name="step"]:not([value="back"])')).to_have_value("study_status")
    expect(page.get_by_text("Océane")).to_be_visible()


def test_closing_the_funnel_wipes_progress(page, funnel_url, beneficiary_mode):
    page.goto(funnel_url)
    _complete_email_step(page)
    expect(page.locator('input[name="step"]:not([value="back"])')).to_have_value("identity")

    page.locator("[data-funnel-close]").click()
    page.goto(funnel_url)

    # Coming back after an explicit exit starts a fresh funnel, not a resumed one.
    expect(page.locator('input[name="step"]:not([value="back"])')).to_have_value("email")
    expect(page.locator('input[name="email"]')).to_have_value("")


def test_age_gate_wipes_progress(page, funnel_url, beneficiary_mode):
    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page, birth_date="1990-01-01")

    expect(page.get_by_role("link", name="Rejoindre la coalition")).to_be_visible()

    page.goto(funnel_url)
    expect(page.locator('input[name="step"]:not([value="back"])')).to_have_value("email")
    expect(page.locator('input[name="email"]')).to_have_value("")
