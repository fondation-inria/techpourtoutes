from playwright.sync_api import expect

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


def test_edit_user_empties_the_school_search_of_another_structure_type(page, live_server, pro):
    pro.structure_type = "school"
    pro.structure_name = "Lycée Voltaire"
    pro.save()
    page.goto(f"{live_server.url}/se-connecter/token/{pro.issue_login_token()}/")
    page.goto(f"{live_server.url}/mon-compte/profil/")
    page.get_by_role("button", name="Modifier").first.click()
    saved_school = page.get_by_text("Lycée Voltaire", exact=True)
    expect(saved_school).to_be_visible()

    select_option(page, STRUCTURE_TYPE, "Établissement du supérieur")
    expect(saved_school).to_have_count(0)
    expect(page.get_by_label("Établissement")).to_have_value("")
    expect(page.locator('input[name="structure_name"]')).to_have_value("")

    select_option(page, STRUCTURE_TYPE, "Collège ou lycée")
    expect(saved_school).to_be_visible()
