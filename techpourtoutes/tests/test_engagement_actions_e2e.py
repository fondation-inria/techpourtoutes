import re
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from playwright.sync_api import expect

from techpourtoutes.models import Pro

# These tests drive a real browser through the five coalition engagement landing pages,
# covering what view tests can't: the Alpine-driven form reveal, the custom dropdowns, and
# the HTMX-backed school autocompletes.

JOBIRL_TEST_URL = "https://preprod.jobirl.com"


def test_mentor_signup_creates_pro_and_sends_welcome_email(
    page, live_server, httpx_mock, mailoutbox
):
    with override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY="test-api-key"):
        httpx_mock.add_response(
            url=f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_register",
            status_code=200,
            json={"response": "success", "datas": {"id": 42, "token": "tok-abc"}},
        )

        page.goto(f"{live_server.url}{reverse('mentor_landing')}")
        _reveal_form(page, "mentor-member-card")

        _fill_identity(
            page, first_name="Alice", last_name="Martin", email="alice.mentor@example.com"
        )
        page.fill('input[name="phone"]', "0612345678")
        page.fill('input[name="postal_code"]', "75001")
        _select_custom_dropdown(
            page, field_id="id_professional_situation", option_label="À la retraite"
        )
        page.fill('input[name="job_title"]', "Retraitée")
        _accept_terms(page)
        page.locator("#mentor-form-card").get_by_role("button", name="Je deviens mentor").click()

        expect(page).to_have_url(re.compile(r"/bienvenue-dans-la-coalition/$"))
        pro = Pro.objects.get(email="alice.mentor@example.com")
        assert "mentor" in pro.engagements
        assert len(mailoutbox) == 1


def test_work_ambassador_signup_creates_pro_and_sends_welcome_email(page, live_server, mailoutbox):
    page.goto(f"{live_server.url}{reverse('work_ambassador_landing')}")
    _reveal_form(page, "work-ambassador-member-card")

    _fill_identity(page, first_name="Bea", last_name="Dupuis", email="bea.ambassador@example.com")
    page.fill('input[name="phone"]', "0612345678")
    page.fill('input[name="postal_code"]', "75001")
    _select_custom_dropdown(
        page, field_id="id_professional_situation", option_label="À la retraite"
    )
    page.fill('input[name="job_title"]', "Retraitée")
    _accept_terms(page)
    page.locator("#work-ambassador-form-card").get_by_role(
        "button", name="Je deviens ambassadrice"
    ).click()

    expect(page).to_have_url(re.compile(r"/bienvenue-dans-la-coalition/$"))
    pro = Pro.objects.get(email="bea.ambassador@example.com")
    assert "work_ambassador" in pro.engagements
    assert len(mailoutbox) == 2


def test_sponsor_signup_creates_pro_and_sends_welcome_email(page, live_server, mailoutbox):
    page.goto(f"{live_server.url}{reverse('sponsor_landing')}")
    _reveal_form(page, "sponsor-member-card")

    _fill_identity(
        page, first_name="Chloé", last_name="Bernard", email="chloe.sponsor@example.com"
    )
    page.fill('input[name="phone"]', "0612345678")
    page.fill('input[name="postal_code"]', "75001")
    page.fill('input[name="job_title"]', "Directrice")
    page.fill('input[name="structure_name"]', "Grande entreprise")
    _accept_terms(page)
    page.locator("#sponsor-form-card").get_by_role("button", name="Je deviens mécène").click()

    expect(page).to_have_url(re.compile(r"/bienvenue-dans-la-coalition/$"))
    pro = Pro.objects.get(email="chloe.sponsor@example.com")
    assert "sponsor" in pro.engagements
    assert len(mailoutbox) == 2


def test_training_ambassador_signup_creates_pro_and_training_experience(
    page, live_server, higher_ed_school, higher_ed_formation, mailoutbox
):
    page.goto(f"{live_server.url}{reverse('training_ambassador_landing')}")
    _reveal_form(page, "training-ambassador-member-card")

    _fill_identity(page, first_name="Dina", last_name="Faure", email="dina.training@example.com")
    page.fill('input[name="phone"]', "0612345678")
    page.fill("#id_school_label", higher_ed_school.name)
    page.get_by_role("option", name=higher_ed_school.display_label).click()
    page.fill("#id_formation_label", higher_ed_formation.name)
    page.get_by_role("option", name=higher_ed_formation.name).click()
    _accept_terms(page)
    page.locator("#training-ambassador-form-card").get_by_role(
        "button", name="Je deviens ambassadrice"
    ).click()

    expect(page).to_have_url(re.compile(r"/bienvenue-dans-la-coalition/$"))
    pro = Pro.objects.get(email="dina.training@example.com")
    assert "training_ambassador" in pro.engagements
    experience = pro.training_experiences.get()
    assert experience.school_id == higher_ed_school.id
    assert experience.formation_id == higher_ed_formation.id
    assert len(mailoutbox) == 3


def test_workshops_signup_creates_pro_and_workshop_requests(page, live_server, school, mailoutbox):
    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task"):
        page.goto(f"{live_server.url}{reverse('workshops_landing')}")
        page.locator("#latitudes-cta").click()

        _fill_identity(
            page, first_name="Elsa", last_name="Girard", email="elsa.workshop@example.com"
        )
        _select_custom_dropdown(page, field_id="id_job_title", option_label="Enseignante")
        page.fill("#id_school_label", school.name)
        page.get_by_role("option", name=f"{school.name} ({school.postal_code})").click()
        _check(page, 'input[name="ateliers"][value="future_of_tech"]')
        _accept_terms(page)
        page.locator("#latitudes-form-card").get_by_role(
            "button", name="Je demande un atelier Latitudes"
        ).click()

        expect(page).to_have_url(re.compile(r"/bienvenue-dans-la-coalition/$"))
        pro = Pro.objects.get(email="elsa.workshop@example.com")
        assert "workshops" in pro.engagements
        assert pro.workshop_requests.get().type == "future_of_tech"
        assert len(mailoutbox) == 1


def _reveal_form(page, member_card_id):
    page.locator(f"#{member_card_id}").get_by_role("button").click()


def _check(page, selector):
    # The radio/checkbox <input> itself is sr-only (invisible, zero-size); the visible control
    # is its sibling ".tick-base" span, styled to look checked/unchecked via peer-checked. Click
    # that sibling instead: Playwright refuses to click the invisible input directly.
    page.locator(f"label:has({selector}) .tick-base").click()


def _fill_identity(page, *, first_name, last_name, email):
    _check(page, 'input[name="civility"][value="Madame"]')
    page.fill('input[name="first_name"]', first_name)
    page.fill('input[name="last_name"]', last_name)
    page.fill('input[name="email"]', email)


def _accept_terms(page):
    _check(page, 'input[name="terms_accepted"]')
    _check(page, 'input[name="manifeste_accepted"]')


def _select_custom_dropdown(page, *, field_id, option_label):
    page.locator(f"#{field_id}").click()
    page.get_by_role("button", name=option_label, exact=True).click()
