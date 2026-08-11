import re

import pytest
from playwright.sync_api import expect
from waffle.testutils import override_switch

from techpourtoutes.models import Beneficiary, School, TrainingExperience, User
from techpourtoutes.utils.school_year import current_school_year_start_date

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
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("email")
    page.fill('input[name="email"]', email)
    page.get_by_role("button", name="Continuer").click()
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("identity")


def _complete_identity_step(page, birth_date="2005-01-01"):
    page.fill('input[name="first_name"]', "Océane")
    page.fill('input[name="last_name"]', "Durand")
    page.fill('input[name="birth_date"]', birth_date)
    page.locator('input[name="age_eligibility_accepted"]').check(force=True)
    page.locator('input[name="terms_accepted"]').check(force=True)
    page.get_by_role("button", name="Continuer").click()


def _go_back(page):
    page.get_by_role("button", name="Retour").click()


def _choose_study_status(page, label):
    page.get_by_text(label).click()
    page.get_by_role("button", name="Continuer").click()


def _select_option(page, label, option):
    page.get_by_role("button", name=label).click()
    page.get_by_role("button", name=option, exact=True).click()


def test_graduate_registers_with_her_last_diploma(page, funnel_url, beneficiary_mode):
    School(identifier="0750001A", name="Lycée Voltaire", postal_code="75011").save()
    diploma_year = current_school_year_start_date().year - 3

    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    _choose_study_status(page, "J'ai terminé mes études")

    _select_option(page, "En quelle année", f"{diploma_year}-{diploma_year + 1}")
    # A diploma can come from either list, so no establishment is offered before the level.
    expect(page.locator('input[name="q"]')).to_have_count(0)
    _select_option(page, "Quel est le niveau de ton diplôme ?*", "Terminale")

    page.fill('input[name="q"]', "voltaire")
    page.get_by_role("button", name="Lycée Voltaire (75011)").click()
    page.fill('input[name="course"]', "Bac général")
    page.get_by_role("button", name="Rejoindre le club").click()

    expect(page.get_by_text("Saisis le code")).to_be_visible()
    experience = TrainingExperience.objects.get(
        user=Beneficiary.objects.get(email="oceane@example.com")
    )
    assert experience.school.identifier == "0750001A"
    assert experience.level == TrainingExperience.Level.TERMINALE
    assert experience.course == "Bac général"
    assert experience.start_date.year == diploma_year


def test_changing_the_diploma_level_swaps_the_establishment_list(
    page, funnel_url, beneficiary_mode
):
    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    _choose_study_status(page, "J'ai terminé mes études")

    _select_option(page, "Quel est le niveau de ton diplôme ?*", "Terminale")
    expect(page.get_by_text("Recherche par nom et/ou code postal")).to_be_visible()

    _select_option(page, "Quel est le niveau de ton diplôme ?*", "Bac +3")

    expect(page.get_by_text("Recherche par nom et/ou code postal")).to_have_count(0)
    expect(page.get_by_text("Recherche par nom", exact=True)).to_be_visible()


def test_high_schooler_registers_with_her_school(page, funnel_url, beneficiary_mode):
    School(identifier="0750001A", name="Lycée Voltaire", postal_code="75011").save()
    requests = []
    page.on("request", lambda request: requests.append(request.url))

    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    _choose_study_status(page, "Je suis au collège ou au lycée")

    _select_option(page, "En quelle classe es-tu ?*", "Terminale")
    page.fill('input[name="q"]', "voltaire")
    page.get_by_role("button", name="Lycée Voltaire (75011)").click()
    page.fill('input[name="course"]', "Spécialité mathématiques")
    page.get_by_role("button", name="Rejoindre le club").click()

    expect(page.get_by_text("Saisis le code")).to_be_visible()
    experience = TrainingExperience.objects.get(
        user=Beneficiary.objects.get(email="oceane@example.com")
    )
    assert experience.school.identifier == "0750001A"
    assert experience.level == TrainingExperience.Level.TERMINALE
    assert experience.course == "Spécialité mathématiques"
    assert experience.start_date == current_school_year_start_date()

    # The autocomplete fires from inside the funnel form: the collected answers must not ride
    # along on its own request, or they would end up in the query string of every search.
    searches = [url for url in requests if "recherche-etablissements" in url]
    assert searches
    assert not [url for url in searches if "oceane" in url]


def test_a_failed_submit_keeps_the_chosen_school_collapsed(page, funnel_url, beneficiary_mode):
    School(identifier="0750001A", name="Lycée Voltaire", postal_code="75011").save()

    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    _choose_study_status(page, "Je suis au collège ou au lycée")
    _select_option(page, "En quelle classe es-tu ?*", "Terminale")
    page.fill('input[name="q"]', "voltaire")
    page.get_by_role("button", name="Lycée Voltaire (75011)").click()
    # The course is left empty, so the step comes back with an error.
    page.get_by_role("button", name="Rejoindre le club").click()
    expect(page.get_by_text("Ce champ est obligatoire.")).to_be_visible()
    # htmx only wipes what Alpine computed once its settle phase runs, so the screen has to be
    # judged after it — an immediate assertion would pass on a state that lasts milliseconds.
    page.wait_for_timeout(300)

    # The re-rendered screen must show the school as chosen, not the search box reopened
    # underneath it.
    expect(page.locator('input[name="q"]')).to_be_hidden()
    expect(page.get_by_text("Lycée Voltaire (75011)")).to_be_visible()


def test_reload_keeps_progress(page, funnel_url, beneficiary_mode):
    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("study_status")

    page.reload()

    # The stored answers are re-hydrated from sessionStorage and the funnel resumes where it was.
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("study_status")
    expect(page.get_by_text("Océane")).to_be_visible()


def test_closing_the_funnel_wipes_progress(page, funnel_url, beneficiary_mode):
    page.goto(funnel_url)
    _complete_email_step(page)
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("identity")

    page.locator("[data-funnel-close]").click()
    page.goto(funnel_url)

    # Coming back after an explicit exit starts a fresh funnel, not a resumed one.
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("email")
    expect(page.locator('input[name="email"]')).to_have_value("")


def test_unchecking_a_box_after_going_back_is_kept(page, funnel_url, beneficiary_mode):
    page.goto(funnel_url)
    _complete_email_step(page)
    page.locator('input[name="newsletter_consent"]').check(force=True)
    _complete_identity_step(page)
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("study_status")

    _go_back(page)
    expect(page.locator('input[name="newsletter_consent"]')).to_be_checked()
    page.locator('input[name="newsletter_consent"]').uncheck(force=True)
    page.get_by_role("button", name="Continuer").click()
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("study_status")

    # An unchecked box must clear its stored answer, not fall back to the one sent the first time.
    _go_back(page)
    expect(page.locator('input[name="newsletter_consent"]')).not_to_be_checked()


def test_unchecking_a_required_box_after_going_back_blocks_the_step(
    page, funnel_url, beneficiary_mode
):
    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("study_status")

    _go_back(page)
    page.locator('input[name="age_eligibility_accepted"]').uncheck(force=True)
    page.get_by_role("button", name="Continuer").click()

    expect(
        page.get_by_text("Tu dois confirmer être éligible au programme pour continuer.")
    ).to_be_visible()
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("identity")


def test_existing_email_wipes_progress(page, funnel_url, beneficiary_mode):
    User.objects.create_user(
        username="taken@example.com",
        email="taken@example.com",
        password="irrelevant",
        first_name="Taken",
        last_name="User",
    )
    page.goto(funnel_url)
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("email")
    page.fill('input[name="email"]', "taken@example.com")
    page.get_by_role("button", name="Continuer").click()

    expect(page).to_have_url(re.compile("se-connecter"))

    # The email can never be submitted, so nothing of the funnel should survive the redirect.
    page.goto(funnel_url)
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("email")
    expect(page.locator('input[name="email"]')).to_have_value("")


def test_age_gate_wipes_progress(page, funnel_url, beneficiary_mode):
    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page, birth_date="1990-01-01")

    expect(page.get_by_role("link", name="Rejoindre la coalition")).to_be_visible()

    page.goto(funnel_url)
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("email")
    expect(page.locator('input[name="email"]')).to_have_value("")
