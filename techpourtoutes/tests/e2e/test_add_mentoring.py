import re

import pytest
from playwright.sync_api import expect

from techpourtoutes.models import Beneficiary, Level, TrainingExperience
from techpourtoutes.utils.dates import adult_birth_date
from techpourtoutes.utils.school_year import (
    current_school_year_end_date,
    current_school_year_start_date,
)

from .helpers import (
    HIGH_SCHOOL_FORMATION_LABEL,
    HIGH_SCHOOL_LABEL,
    choose_study_status,
    pick,
    select_option,
    voltaire_teaching,
)

# These tests drive a real browser to cover what the view tests cannot: an account imported from
# Faveod carries neither a birth date nor a parcours, and both gaps are only resolved client-side
# — minority as she picks a date, the parcours questions as she picks a study status.

_LEGAL_REPRESENTATIVE_NAME = 'input[name="legal_representative_name"]'
_LEGAL_REPRESENTATIVE_EMAIL = 'input[name="legal_representative_email"]'


def _beneficiary():
    beneficiary = Beneficiary(
        username="oceane@example.com",
        first_name="Océane",
        last_name="Martin",
        email="oceane@example.com",
    )
    beneficiary.save()
    return beneficiary


def _sign_in(live_server, page, beneficiary):
    page.goto(f"{live_server.url}/se-connecter/token/{beneficiary.issue_login_token()}/")
    page.goto(f"{live_server.url}/devenir-mentoree/")
    return page


@pytest.fixture
def page_without_birth_date(live_server, page, db):
    """Only the birth date is missing: the parcours is already on file."""
    beneficiary = _beneficiary()
    school, formation = voltaire_teaching("Bac général")
    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        formation=formation,
        level=Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=current_school_year_end_date(),
    )
    return _sign_in(live_server, page, beneficiary)


@pytest.fixture
def page_without_parcours(live_server, page, db):
    """The full Faveod gap: neither birth date nor parcours."""
    voltaire_teaching("Bac général")
    return _sign_in(live_server, page, _beneficiary())


def _birth_date_for_age(age):
    cutoff = adult_birth_date()
    return cutoff.replace(year=cutoff.year + 18 - age).isoformat()


# ------------------- the birth date gap -------------------


def test_the_legal_representative_fields_stay_hidden_until_a_birth_date_is_picked(
    page_without_birth_date,
):
    expect(page_without_birth_date.locator(_LEGAL_REPRESENTATIVE_EMAIL)).to_be_hidden()
    expect(page_without_birth_date.get_by_text("Comme tu es mineure")).to_be_hidden()


def test_picking_a_minor_birth_date_reveals_the_legal_representative_fields(
    page_without_birth_date,
):
    page_without_birth_date.fill('input[name="birth_date"]', _birth_date_for_age(16))

    expect(page_without_birth_date.locator(_LEGAL_REPRESENTATIVE_NAME)).to_be_visible()
    expect(page_without_birth_date.locator(_LEGAL_REPRESENTATIVE_EMAIL)).to_be_visible()
    expect(page_without_birth_date.get_by_text("Comme tu es mineure")).to_be_visible()


def test_picking_an_adult_birth_date_keeps_the_legal_representative_fields_hidden(
    page_without_birth_date,
):
    page_without_birth_date.fill('input[name="birth_date"]', _birth_date_for_age(20))

    expect(page_without_birth_date.locator(_LEGAL_REPRESENTATIVE_EMAIL)).to_be_hidden()
    expect(
        page_without_birth_date.get_by_text("nous avons besoin de ta date de naissance")
    ).to_be_visible()


def test_correcting_a_minor_birth_date_to_an_adult_one_hides_the_fields_again(
    page_without_birth_date,
):
    page_without_birth_date.fill('input[name="birth_date"]', _birth_date_for_age(16))
    expect(page_without_birth_date.locator(_LEGAL_REPRESENTATIVE_EMAIL)).to_be_visible()

    page_without_birth_date.fill('input[name="birth_date"]', _birth_date_for_age(20))

    expect(page_without_birth_date.locator(_LEGAL_REPRESENTATIVE_EMAIL)).to_be_hidden()


def test_a_minor_signs_up_in_a_single_submit(page_without_birth_date):
    page_without_birth_date.fill('input[name="birth_date"]', _birth_date_for_age(16))
    page_without_birth_date.fill('input[name="phone"]', "0612345678")
    page_without_birth_date.fill(_LEGAL_REPRESENTATIVE_NAME, "Hedy Lamarr")
    page_without_birth_date.fill(_LEGAL_REPRESENTATIVE_EMAIL, "hedy@example.com")

    page_without_birth_date.get_by_role("button", name="Rejoindre le mentorat").click()

    expect(page_without_birth_date).to_have_url(re.compile(r"/mon-compte/$"))
    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.legal_representative_email == "hedy@example.com"


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
        page_without_parcours.get_by_role(
            "button", name="En quelle année as-tu obtenu ton dernier diplôme ?*"
        )
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

    page_without_parcours.fill('input[name="birth_date"]', _birth_date_for_age(16))
    page_without_parcours.fill('input[name="phone"]', "0612345678")
    page_without_parcours.fill(_LEGAL_REPRESENTATIVE_NAME, "Hedy Lamarr")
    page_without_parcours.fill(_LEGAL_REPRESENTATIVE_EMAIL, "hedy@example.com")
    page_without_parcours.get_by_role("button", name="Rejoindre le mentorat").click()

    expect(page_without_parcours).to_have_url(re.compile(r"/mon-compte/$"))
    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.legal_representative_email == "hedy@example.com"
    assert beneficiary.training_experiences.count() == 1
