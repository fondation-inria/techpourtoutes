from datetime import date

from playwright.sync_api import expect

from techpourtoutes.models import TrainingExperience
from techpourtoutes.models.level import Level

from .helpers import select_option

# The structure name only means something once she works in a structure: like the inscription
# funnel, the account form hides it as soon as she says she is retired or jobless.

STRUCTURE_TYPE = "Type de structure*"


def test_edit_user_hides_the_structure_name_of_a_pro_without_a_structure(page, live_server, pro):
    pro.structure_type = "company"
    pro.save()
    page.goto(f"{live_server.url}/se-connecter/token/{pro.issue_login_token()}/")
    page.goto(f"{live_server.url}/mon-compte/profil/")
    page.get_by_role("button", name="Modifier").first.click()
    structure_name = page.locator('input[name="structure_name"]')
    expect(structure_name).to_be_visible()

    select_option(page, STRUCTURE_TYPE, "Je suis à la retraite")
    expect(structure_name).to_be_hidden()

    select_option(page, STRUCTURE_TYPE, "Entreprise")
    expect(structure_name).to_be_visible()


# Each section of the profile swaps for its form and back: the focus goes to the form, then back
# to the button that opened it, or a screen reader is left at the top of the page.

EDIT_USER_INFO = "Modifier les informations personnelles"


def _edit_user_info(page, live_server, pro):
    pro.structure_type = "company"
    pro.save()
    page.goto(f"{live_server.url}/se-connecter/token/{pro.issue_login_token()}/")
    page.goto(f"{live_server.url}/mon-compte/profil/")
    page.get_by_role("button", name=EDIT_USER_INFO).click()


def test_edit_user_focuses_the_title_of_the_form(page, live_server, pro):
    _edit_user_info(page, live_server, pro)

    expect(page.get_by_role("heading", name="Informations personnelles")).to_be_focused()


def test_update_user_gives_the_focus_back_to_the_edit_button(page, live_server, pro):
    _edit_user_info(page, live_server, pro)

    page.get_by_role("button", name="Sauvegarder").click()
    expect(page.get_by_role("button", name=EDIT_USER_INFO)).to_be_focused()


def test_show_user_info_gives_the_focus_back_to_the_edit_button(page, live_server, pro):
    _edit_user_info(page, live_server, pro)

    page.get_by_role("button", name="Annuler").click()
    expect(page.get_by_role("button", name=EDIT_USER_INFO)).to_be_focused()


def test_show_user_focuses_nothing_on_load(page, live_server, pro):
    page.goto(f"{live_server.url}/se-connecter/token/{pro.issue_login_token()}/")
    page.goto(f"{live_server.url}/mon-compte/profil/")

    assert page.evaluate("document.activeElement === document.body")


def test_update_user_keeps_the_focus_on_a_form_sent_back_with_its_errors(page, live_server, pro):
    _edit_user_info(page, live_server, pro)
    page.get_by_label("Prénom*").fill("")

    page.get_by_role("button", name="Sauvegarder").click()
    expect(page.get_by_text("Ce champ est obligatoire.")).to_be_visible()
    expect(page.get_by_role("heading", name="Informations personnelles")).to_be_focused()


def _open_profile_of(page, live_server, beneficiary):
    page.goto(f"{live_server.url}/se-connecter/token/{beneficiary.issue_login_token()}/")
    page.goto(f"{live_server.url}/mon-compte/profil/")


def test_edit_beneficiary_training_experience_focuses_the_delete_button_then_the_year(
    page, live_server, beneficiary, beneficiary_experience
):
    _open_profile_of(page, live_server, beneficiary)

    page.get_by_role("button", name="Modifier la formation – 2023-2024").click()
    expect(page.get_by_role("button", name="Supprimer cette année")).to_be_focused()
    # The browser honours `autofocus` on insertion, htmx again once it settles: Tab in between
    # would be undone.
    page.wait_for_function("!document.querySelector('.htmx-added')")
    page.keyboard.press("Tab")
    expect(
        page.locator("#beneficiary-training-experiences form button[aria-expanded]").first
    ).to_be_focused()


def test_edit_beneficiary_training_experience_focuses_the_enrolment_of_the_current_one(
    page, live_server, beneficiary
):
    _open_profile_of(page, live_server, beneficiary)

    page.get_by_role("button", name="Modifier la formation – Année scolaire en cours").click()
    expect(
        page.locator("#beneficiary-training-experiences form input[type=checkbox]")
    ).to_be_focused()


def test_show_beneficiary_training_experience_gives_the_focus_back_to_its_edit_button(
    page, live_server, beneficiary, beneficiary_experience
):
    _open_profile_of(page, live_server, beneficiary)
    page.get_by_role("button", name="Modifier la formation – 2023-2024").click()

    page.get_by_role("button", name="Annuler").click()
    expect(page.get_by_role("button", name="Modifier la formation – 2023-2024")).to_be_focused()


def test_new_beneficiary_training_experience_focuses_its_year(page, live_server, beneficiary):
    _open_profile_of(page, live_server, beneficiary)

    page.get_by_role("button", name="Ajouter une année").click()
    expect(
        page.locator("#beneficiary-training-experiences form button[aria-expanded]").first
    ).to_be_focused()


def test_new_beneficiary_training_experience_cancelled_focuses_the_add_button(
    page, live_server, beneficiary
):
    _open_profile_of(page, live_server, beneficiary)
    page.get_by_role("button", name="Ajouter une année").click()

    page.get_by_role("button", name="Annuler").click()
    expect(page.get_by_role("button", name="Ajouter une année")).to_be_focused()


def test_destroy_beneficiary_training_experience_focuses_the_add_button(
    page, live_server, beneficiary, beneficiary_experience, school, formation
):
    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        formation=formation,
        level=Level.PREMIERE,
        start_date=date(2022, 9, 1),
        end_date=date(2023, 8, 31),
    )
    _open_profile_of(page, live_server, beneficiary)
    page.get_by_role("button", name="Modifier la formation – 2023-2024").click()
    page.once("dialog", lambda dialog: dialog.accept())

    page.get_by_role("button", name="Supprimer cette année").click()
    expect(page.get_by_role("button", name="Modifier la formation – 2023-2024")).to_have_count(0)
    expect(page.get_by_role("button", name="Ajouter une année")).to_be_focused()


def test_edit_user_email_focuses_the_email_field(page, live_server, beneficiary):
    _open_profile_of(page, live_server, beneficiary)

    page.get_by_role("button", name="Changer mon adresse mail").click()
    expect(page.locator("#account-email-section input[name=email]")).to_be_focused()


def test_show_user_email_gives_the_focus_back_to_its_button(page, live_server, beneficiary):
    _open_profile_of(page, live_server, beneficiary)
    page.get_by_role("button", name="Changer mon adresse mail").click()

    page.locator("#account-email-section").get_by_role("button", name="Annuler").click()
    expect(page.get_by_role("button", name="Changer mon adresse mail")).to_be_focused()


def test_destroy_beneficiary_training_experience_keeps_the_focus_on_a_failed_delete(
    page, live_server, beneficiary, beneficiary_experience, school, formation
):
    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        formation=formation,
        level=Level.PREMIERE,
        start_date=date(2022, 9, 1),
        end_date=date(2023, 8, 31),
    )
    _open_profile_of(page, live_server, beneficiary)
    page.get_by_role("button", name="Modifier la formation – 2023-2024").click()
    page.route("**/supprimer/", lambda route: route.fulfill(status=500))
    page.once("dialog", lambda dialog: dialog.accept())

    page.get_by_role("button", name="Supprimer cette année").click()
    expect(page.get_by_role("button", name="Supprimer cette année")).to_be_focused()
