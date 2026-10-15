import re

import pytest
from playwright.sync_api import expect

from techpourtoutes.models import Beneficiary
from techpourtoutes.tests.birth_dates import birth_date_for_age

from .helpers import (
    HIGH_SCHOOL_FORMATION_LABEL,
    HIGH_SCHOOL_LABEL,
    choose_study_status,
    pick,
    select_option,
    voltaire_teaching,
)

# These tests drive a real browser to cover what the view tests cannot: an account imported from
# Faveod carries no parcours, and the gap is only resolved client-side — the parcours questions
# as she picks a study status.

_LEGAL_REPRESENTATIVE_NAME = 'input[name="legal_representative_name"]'
_LEGAL_REPRESENTATIVE_EMAIL = 'input[name="legal_representative_email"]'


def _beneficiary():
    beneficiary = Beneficiary(
        username="oceane@example.com",
        first_name="Océane",
        last_name="Martin",
        email="oceane@example.com",
        birth_date=birth_date_for_age(16),
    )
    beneficiary.save()
    return beneficiary


def _sign_in(live_server, page, beneficiary):
    page.goto(f"{live_server.url}/se-connecter/token/{beneficiary.issue_login_token()}/")
    page.goto(f"{live_server.url}/devenir-mentoree/")
    return page


@pytest.fixture
def page_without_parcours(live_server, page, db):
    """The Faveod gap: no parcours."""
    voltaire_teaching("Bac général")
    return _sign_in(live_server, page, _beneficiary())


# ------------------- the parcours gap -------------------


def _expect_step(page, step):
    """The step swaps in without a reload, so the assertion has to wait for it."""
    expect(page.locator('#mentoring-step input[name="action"]')).to_have_value(step)


def test_an_account_without_a_parcours_starts_on_the_study_status(page_without_parcours):
    expect(page_without_parcours.get_by_text("Où en es-tu dans tes études ?")).to_be_visible()
    _expect_step(page_without_parcours, "study_status")


def test_the_study_status_leads_to_the_matching_parcours_questions(page_without_parcours):
    choose_study_status(page_without_parcours, "Je suis au collège ou au lycée")

    _expect_step(page_without_parcours, "training_experience")
    expect(page_without_parcours.get_by_label(HIGH_SCHOOL_LABEL)).to_be_visible()
    expect(page_without_parcours.get_by_label(HIGH_SCHOOL_FORMATION_LABEL)).to_be_visible()


def test_a_graduate_gets_the_year_question_instead(page_without_parcours):
    choose_study_status(page_without_parcours, "J'ai terminé mes études")

    _expect_step(page_without_parcours, "training_experience")
    expect(
        page_without_parcours.get_by_role("button", name="En quelle année était-ce ?*")
    ).to_be_visible()


def test_the_parcours_step_leads_to_the_mentoring_questions(page_without_parcours):
    choose_study_status(page_without_parcours, "Je suis au collège ou au lycée")
    select_option(page_without_parcours, "En quelle classe es-tu ?*", "Terminale")
    pick(page_without_parcours, HIGH_SCHOOL_LABEL, "voltaire", "Lycée Voltaire (75011)")
    pick(page_without_parcours, HIGH_SCHOOL_FORMATION_LABEL, "bac", "Bac général")
    page_without_parcours.get_by_role("button", name="Continuer").click()

    _expect_step(page_without_parcours, "mentoring_signup")
    experience = Beneficiary.objects.get(email="oceane@example.com").training_experiences.get()
    assert experience.school.name == "Lycée Voltaire"
    assert experience.formation.name == "Bac général"


def test_a_faveod_account_walks_the_three_steps_to_the_end(page_without_parcours):
    choose_study_status(page_without_parcours, "Je suis au collège ou au lycée")
    select_option(page_without_parcours, "En quelle classe es-tu ?*", "Terminale")
    pick(page_without_parcours, HIGH_SCHOOL_LABEL, "voltaire", "Lycée Voltaire (75011)")
    pick(page_without_parcours, HIGH_SCHOOL_FORMATION_LABEL, "bac", "Bac général")
    page_without_parcours.get_by_role("button", name="Continuer").click()

    page_without_parcours.fill('input[name="phone"]', "0612345678")
    page_without_parcours.fill(_LEGAL_REPRESENTATIVE_NAME, "Hedy Lamarr")
    page_without_parcours.fill(_LEGAL_REPRESENTATIVE_EMAIL, "hedy@example.com")
    page_without_parcours.get_by_role("button", name="Rejoindre le mentorat").click()

    expect(page_without_parcours).to_have_url(re.compile(r"/mon-compte/$"))
    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.legal_representative_email == "hedy@example.com"
    assert beneficiary.training_experiences.count() == 1
