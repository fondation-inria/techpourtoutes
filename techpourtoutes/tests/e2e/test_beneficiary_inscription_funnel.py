import re

import pytest
from playwright.sync_api import expect

from techpourtoutes.models import (
    Beneficiary,
    Formation,
    Level,
    TrainingExperience,
    User,
)
from techpourtoutes.utils.school_year import current_school_year_start_date

from .helpers import (
    HIGH_SCHOOL_FORMATION_LABEL,
    HIGH_SCHOOL_LABEL,
    choose_study_status,
    pick,
    search_field,
    select_option,
    voltaire_teaching,
)

# These tests drive a real browser to cover what the view tests cannot: the client-side
# sessionStorage behaviour (survive reload, wipe on explicit exit) wired through Alpine + HTMX.


_DIPLOMA_SCHOOL_LABEL = "Dans quel établissement as-tu obtenu ce diplôme ?*"
_DIPLOMA_FORMATION_LABEL = "De quelle formation es-tu diplômée ?*"


@pytest.fixture
def funnel_url(live_server):
    return f"{live_server.url}/inscription/"


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


def test_graduate_registers_with_her_last_diploma(page, funnel_url):
    _, formation = voltaire_teaching("Bac général")
    diploma_year = current_school_year_start_date().year - 3

    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    choose_study_status(page, "J'ai terminé mes études")

    select_option(page, "En quelle année", f"{diploma_year}-{diploma_year + 1}")
    # A diploma can come from either list, so no establishment is offered before the level.
    expect(search_field(page, _DIPLOMA_SCHOOL_LABEL)).to_have_count(0)
    select_option(page, "Quel est le niveau de ton diplôme ?*", "Terminale")

    pick(page, _DIPLOMA_SCHOOL_LABEL, "voltaire", "Lycée Voltaire (75011)")
    pick(page, _DIPLOMA_FORMATION_LABEL, "bac", "Bac général")
    page.get_by_role("button", name="Rejoindre le club").click()

    expect(page.get_by_text("Saisis le code")).to_be_visible()
    experience = TrainingExperience.objects.get(
        user=Beneficiary.objects.get(email="oceane@example.com")
    )
    assert experience.school.uai == "0750001A"
    assert experience.level == Level.TERMINALE
    assert experience.formation == formation
    assert experience.start_date.year == diploma_year


def test_the_formation_field_waits_for_the_school(page, funnel_url):
    voltaire_teaching("Spécialité mathématiques")

    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    choose_study_status(page, "Je suis au collège ou au lycée")
    select_option(page, "En quelle classe es-tu ?*", "Terminale")

    formation_field = search_field(page, HIGH_SCHOOL_FORMATION_LABEL)
    expect(formation_field).to_be_disabled()

    pick(page, HIGH_SCHOOL_LABEL, "voltaire", "Lycée Voltaire (75011)")

    expect(formation_field).to_be_enabled()


def test_clearing_the_school_empties_and_disables_the_formation(page, funnel_url):
    voltaire_teaching("Spécialité mathématiques")

    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    choose_study_status(page, "Je suis au collège ou au lycée")
    select_option(page, "En quelle classe es-tu ?*", "Terminale")
    pick(page, HIGH_SCHOOL_LABEL, "voltaire", "Lycée Voltaire (75011)")
    pick(page, HIGH_SCHOOL_FORMATION_LABEL, "specialite", "Spécialité mathématiques")

    # The first clear button is the school's: dropping it must take the formation down with it.
    page.get_by_role("button", name="Effacer la sélection").first.click()

    expect(page.locator('input[name="formation_id"]')).to_have_value("")
    expect(search_field(page, HIGH_SCHOOL_FORMATION_LABEL)).to_be_disabled()


def test_changing_the_diploma_level_swaps_the_establishment_list(page, funnel_url):
    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    choose_study_status(page, "J'ai terminé mes études")

    # Each perimeter owns its own dropdown container, the higher-ed one suffixed "-sup".
    higher_ed_dropdown = page.locator('[id^="school-results-"][id$="-sup"]')

    select_option(page, "Quel est le niveau de ton diplôme ?*", "Terminale")
    expect(page.get_by_text("Recherche par nom et/ou code postal")).to_be_visible()
    expect(higher_ed_dropdown).to_have_count(0)

    select_option(page, "Quel est le niveau de ton diplôme ?*", "Bac +3")

    expect(page.get_by_text("Recherche par nom et/ou code postal")).to_have_count(0)
    expect(higher_ed_dropdown).to_have_count(1)


def test_high_schooler_registers_with_her_school(page, funnel_url):
    _, formation = voltaire_teaching("Spécialité mathématiques")
    requests = []
    page.on("request", lambda request: requests.append(request.url))

    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    choose_study_status(page, "Je suis au collège ou au lycée")

    select_option(page, "En quelle classe es-tu ?*", "Terminale")
    pick(page, HIGH_SCHOOL_LABEL, "voltaire", "Lycée Voltaire (75011)")
    pick(page, HIGH_SCHOOL_FORMATION_LABEL, "specialite", "Spécialité mathématiques")
    page.get_by_role("button", name="Rejoindre le club").click()

    expect(page.get_by_text("Saisis le code")).to_be_visible()
    experience = TrainingExperience.objects.get(
        user=Beneficiary.objects.get(email="oceane@example.com")
    )
    assert experience.school.uai == "0750001A"
    assert experience.level == Level.TERMINALE
    assert experience.formation == formation
    assert experience.start_date == current_school_year_start_date()

    # The autocomplete fires from inside the funnel form: the collected answers must not ride
    # along on its own request, or they would end up in the query string of every search.
    searches = [url for url in requests if "recherche-etablissements" in url]
    assert searches
    assert not [url for url in searches if "oceane" in url]


def test_a_failed_submit_keeps_the_chosen_school_collapsed(page, funnel_url):
    voltaire_teaching("Spécialité mathématiques")

    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    choose_study_status(page, "Je suis au collège ou au lycée")
    select_option(page, "En quelle classe es-tu ?*", "Terminale")
    pick(page, HIGH_SCHOOL_LABEL, "voltaire", "Lycée Voltaire (75011)")
    # The formation is left unpicked, so the step comes back with an error.
    page.get_by_role("button", name="Rejoindre le club").click()
    expect(page.get_by_text("Sélectionnez une formation valide.")).to_be_visible()
    # htmx only wipes what Alpine computed once its settle phase runs, so the screen has to be
    # judged after it — an immediate assertion would pass on a state that lasts milliseconds.
    page.wait_for_timeout(300)

    # The re-rendered screen must show the school as chosen, not the search box reopened
    # underneath it.
    expect(search_field(page, HIGH_SCHOOL_LABEL)).to_be_hidden()
    expect(page.get_by_text("Lycée Voltaire (75011)")).to_be_visible()


def test_reload_keeps_progress(page, funnel_url):
    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("study_status")

    page.reload()

    # The stored answers are re-hydrated from sessionStorage and the funnel resumes where it was.
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("study_status")
    expect(page.get_by_text("Océane")).to_be_visible()


def test_closing_the_funnel_wipes_progress(page, funnel_url):
    page.goto(funnel_url)
    _complete_email_step(page)
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("identity")

    page.locator("[data-funnel-close]").click()
    page.goto(funnel_url)

    # Coming back after an explicit exit starts a fresh funnel, not a resumed one.
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("email")
    expect(page.locator('input[name="email"]')).to_have_value("")


def test_unchecking_a_box_after_going_back_is_kept(page, funnel_url):
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


def test_unchecking_a_required_box_after_going_back_blocks_the_step(page, funnel_url):
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


def test_existing_email_wipes_progress(page, funnel_url):
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


def test_age_gate_wipes_progress(page, funnel_url):
    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page, birth_date="1990-01-01")

    expect(page.get_by_role("link", name="Rejoindre la coalition")).to_be_visible()

    page.goto(funnel_url)
    expect(page.locator('input[name="action"]:not([value="back"])')).to_have_value("email")
    expect(page.locator('input[name="email"]')).to_have_value("")


def test_a_missing_school_frees_the_field_and_opens_the_whole_catalogue(page, funnel_url):
    voltaire_teaching("Spécialité mathématiques")
    elsewhere = Formation(onisep_id="9999", name="Bac pro maréchalerie", secondary=True)
    elsewhere.save()

    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    choose_study_status(page, "Je suis au collège ou au lycée")
    select_option(page, "En quelle classe es-tu ?*", "Terminale")

    page.get_by_role("button", name="Je ne trouve pas mon établissement").click()
    search_field(page, HIGH_SCHOOL_LABEL).fill("Lycée du bout du monde")

    # No school to scope on: the formation stays usable and offers what no lycée teaches.
    pick(page, HIGH_SCHOOL_FORMATION_LABEL, "marechalerie", "Bac pro maréchalerie")
    page.get_by_role("button", name="Rejoindre le club").click()

    expect(page.get_by_text("Saisis le code")).to_be_visible()
    experience = TrainingExperience.objects.get(
        user=Beneficiary.objects.get(email="oceane@example.com")
    )
    assert experience.school is None
    assert experience.out_of_scope_school_name == "Lycée du bout du monde"
    assert experience.formation == elsewhere
    assert experience.level == Level.TERMINALE


def test_both_records_missing_registers_on_free_text_alone(page, funnel_url):
    voltaire_teaching("Spécialité mathématiques")

    page.goto(funnel_url)
    _complete_email_step(page)
    _complete_identity_step(page)
    choose_study_status(page, "Je suis au collège ou au lycée")
    select_option(page, "En quelle classe es-tu ?*", "Terminale")

    page.get_by_role("button", name="Je ne trouve pas mon établissement").click()
    search_field(page, HIGH_SCHOOL_LABEL).fill("Lycée du bout du monde")
    page.get_by_role("button", name="Je ne trouve pas ma formation").click()
    search_field(page, HIGH_SCHOOL_FORMATION_LABEL).fill("Bac pro maréchalerie")
    page.get_by_role("button", name="Rejoindre le club").click()

    expect(page.get_by_text("Saisis le code")).to_be_visible()
    experience = TrainingExperience.objects.get(
        user=Beneficiary.objects.get(email="oceane@example.com")
    )
    assert experience.school is None
    assert experience.out_of_scope_school_name == "Lycée du bout du monde"
    assert experience.formation is None
    assert experience.out_of_scope_formation_name == "Bac pro maréchalerie"
    assert experience.level == Level.TERMINALE
