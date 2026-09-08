from playwright.sync_api import expect

from techpourtoutes.models import Event

# This test drives a real browser to cover what the view tests cannot: the modal only exists
# once the page runs, so a view test can see its URL in the markup but not that clicking opens it.


def test_an_anonymous_visitor_is_invited_to_sign_up_before_saving(page, live_server, event):
    event.status = Event.Status.APPROVED
    event.save()
    page.goto(f"{live_server.url}/evenements/")

    page.get_by_label("Enregistrer cet événement").click()

    expect(page.get_by_text("Rejoins le club TechPourToutes")).to_be_visible()
    expect(page.get_by_role("link", name="Créer un compte")).to_be_visible()
