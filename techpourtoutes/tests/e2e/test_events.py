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


def test_the_signup_modal_holds_on_to_the_keyboard(page, live_server, event):
    """Tabbing out of an open modal would hand the keyboard to a page the mouse cannot reach.

    The browser parks the focus on `body` for one step as the cycle wraps, which reaches nothing:
    what must never happen is a control *behind* the modal taking it.
    """
    _open_signup_modal(page, live_server, event)

    for _ in range(6):
        page.keyboard.press("Tab")
        assert page.evaluate(
            "!document.activeElement.matches('a, button, input, select, textarea')"
            " || document.activeElement.closest('dialog') !== null"
        )


def test_escape_closes_the_signup_modal_and_hands_the_focus_back(page, live_server, event):
    bookmark = _open_signup_modal(page, live_server, event)

    page.keyboard.press("Escape")

    expect(page.get_by_text("Rejoins le club TechPourToutes")).to_be_hidden()
    expect(bookmark).to_be_focused()


def _open_signup_modal(page, live_server, event):
    event.status = Event.Status.APPROVED
    event.save()
    page.goto(f"{live_server.url}/evenements/")
    bookmark = page.get_by_label("Enregistrer cet événement")
    bookmark.click()
    expect(page.get_by_text("Rejoins le club TechPourToutes")).to_be_visible()
    return bookmark


def test_the_signup_modal_gives_its_first_tab_to_the_topmost_control(page, live_server, event):
    """Opened with the mouse, a focus placed inside draws no ring: the visitor cannot tell the
    first control already holds it, and reads her first Tab as skipping it."""
    _open_signup_modal(page, live_server, event)

    page.keyboard.press("Tab")

    assert page.evaluate(
        "document.activeElement.matches('dialog [aria-label=\"Fermer\"]:focus-visible')"
    )


def test_the_keyboard_shows_where_it_is_on_an_event_card(page, live_server, event):
    """The card's link is an empty, zero-width anchor: the ring the browser draws on it lands on
    nothing. It has to be drawn on the overlay that does cover the card."""
    event.status = Event.Status.APPROVED
    event.save()
    page.goto(f"{live_server.url}/evenements/")

    assert _tab_until(page, "#events-grid a")

    assert page.evaluate(
        "getComputedStyle(document.activeElement, '::after').outlineStyle !== 'none'"
    )


def test_an_event_card_link_says_which_event_it_opens(page, live_server, event):
    """An empty anchor is announced as a bare "link": the card's name has to reach the link."""
    event.status = Event.Status.APPROVED
    event.save()
    page.goto(f"{live_server.url}/evenements/")

    link = page.get_by_role("link", name=f"Voir l'événement {event.title}")

    expect(link).to_have_count(1)


def _tab_until(page, selector, limit=60):
    for _ in range(limit):
        page.keyboard.press("Tab")
        if page.evaluate("(sel) => document.activeElement.matches(sel)", selector):
            return True
    return False
