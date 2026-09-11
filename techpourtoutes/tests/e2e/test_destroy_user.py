from playwright.sync_api import expect

# The deletion modal is the only one holding a form: its first control is a checkbox whose real
# input is `sr-only`, so nothing but the focus ring can tell the user it has the focus.


def test_the_deletion_modal_gives_its_first_tab_to_the_confirmation_checkbox(
    page, live_server, pro
):
    page.goto(f"{live_server.url}/se-connecter/token/{pro.issue_login_token()}/")
    page.goto(f"{live_server.url}/mon-compte/profil/")
    page.get_by_role("button", name="Supprimer mon compte").click()
    expect(page.get_by_text("vraiment supprimer")).to_be_visible()

    page.keyboard.press("Tab")

    assert page.evaluate("document.activeElement.matches('input[type=checkbox]:focus-visible')")
