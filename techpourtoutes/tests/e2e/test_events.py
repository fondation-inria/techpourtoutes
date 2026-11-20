import re
from datetime import timedelta

from django.utils import timezone
from playwright.sync_api import expect

from techpourtoutes.models import Event

from ..views.test_beneficiary_views import approved_event, save_onsite_event

PLACE_DISABLED_REASON = "Décoche « En ligne uniquement » pour filtrer par région ou département."

# This test drives a real browser to cover what the view tests cannot: the modal only exists
# once the page runs, so a view test can see its URL in the markup but not that clicking opens it.


def test_an_anonymous_visitor_is_invited_to_sign_up_before_saving(page, live_server, event):
    event.status = Event.Status.APPROVED
    event.save()
    page.goto(f"{live_server.url}/evenements/")

    page.get_by_label("Enregistrer cet événement").click()

    expect(page.get_by_text("Rejoins le club TechPourToutes")).to_be_visible()
    expect(page.get_by_role("link", name="Créer un compte")).to_be_visible()


def test_a_date_range_names_the_filter_instead_of_a_selected_filter(page, live_server):
    page.goto(f"{live_server.url}/evenements/")

    dates = page.get_by_role("button", name=re.compile("^Date"))
    dates.click()
    page.get_by_label("À partir du").fill("2026-09-14")
    page.get_by_label("Jusqu'au").fill("2026-10-31")

    expect(dates).to_have_accessible_name("Date\xa0: du 14/09/26 au 31/10/26")
    expect(page.get_by_role("list", name="Date")).not_to_be_visible()

    page.get_by_label("À partir du").fill("")
    page.get_by_label("Jusqu'au").fill("")

    expect(dates).to_have_accessible_name("Date")


def test_clearing_the_dates_keeps_the_other_filters(page, live_server):
    page.goto(f"{live_server.url}/evenements/?date_from=2026-09-14&date_to=2026-10-31&free=1")
    dates = page.get_by_role("button", name=re.compile("^Date"))
    dates.click()
    clear = page.get_by_role("button", name="Effacer les dates")

    clear.click()

    expect(page.get_by_label("À partir du")).to_have_value("")
    expect(page.get_by_label("Jusqu'au")).to_have_value("")
    expect(page.get_by_label("À partir du")).to_be_focused()
    expect(dates).to_have_accessible_name("Date")
    expect(clear).to_be_hidden()
    expect(page).to_have_url(re.compile(r"date_from=&date_to=&free=1"))


def test_an_end_date_typed_before_the_start_date_finds_nothing(page, live_server):
    """The bounds only grey out the picker: typed by hand, an inverted range still searches."""
    page.goto(f"{live_server.url}/evenements/")
    page.get_by_role("button", name="Date").click()
    start = page.get_by_label("À partir du")
    end = page.get_by_label("Jusqu'au")
    expect(start).to_have_attribute("min", "2000-01-01")
    expect(end).to_have_attribute("min", "2000-01-01")

    start.fill("2026-12-10")
    expect(end).to_have_attribute("min", "2026-12-10")
    end.fill("2026-12-20")
    expect(start).to_have_attribute("max", "2026-12-20")

    inverted = page.locator("[aria-live=polite]").get_by_text(
        "La date doit être postérieure à la date de début"
    )
    expect(inverted).to_be_hidden()

    end.press_sequentially("01122026")
    assert end.evaluate("input => input.validity.rangeUnderflow")
    expect(page).to_have_url(re.compile(f"date_to={end.input_value()}"))
    expect(page.get_by_text("Aucun événement ne correspond à ta recherche")).to_be_visible()
    expect(inverted).to_be_visible()
    expect(end).to_have_attribute("aria-invalid", "true")
    expect(end).to_have_accessible_description("La date doit être postérieure à la date de début")

    start.fill("")
    expect(inverted).to_be_hidden()
    expect(end).not_to_have_attribute("aria-invalid", "true")
    end.fill("")
    expect(end).to_have_attribute("min", "2000-01-01")
    expect(start).to_have_attribute("max", "")


def test_a_date_typed_before_2000_is_flagged_under_its_own_field(page, live_server):
    """A year under 1000 is still being typed, digit by digit, so it is left alone until the
    field is left. An end date both before 2000 and before the start only gets the first
    message."""
    too_early = "La date doit être postérieure au 01/01/2000"
    page.goto(f"{live_server.url}/evenements/")
    page.get_by_role("button", name="Date").click()
    start = page.get_by_label("À partir du")
    end = page.get_by_label("Jusqu'au")

    start.fill("0202-11-11")
    expect(start).not_to_have_attribute("aria-invalid", "true")
    start.blur()
    expect(start).to_have_attribute("aria-invalid", "true")

    start.fill("1999-12-31")
    expect(start).to_have_attribute("aria-invalid", "true")
    expect(start).to_have_accessible_description(too_early)
    expect(page.locator("[aria-live=polite]").get_by_text(too_early).first).to_be_visible()

    end.fill("1999-06-01")
    expect(end).to_have_accessible_description(too_early)
    expect(page.get_by_text("La date doit être postérieure à la date de début")).to_be_hidden()

    start.fill("2000-01-01")
    expect(start).not_to_have_attribute("aria-invalid", "true")
    expect(start).to_have_accessible_description("")


def test_dates_typed_digit_by_digit_keep_every_digit(page, live_server):
    """A date input fires `change` on every complete-looking state, a year going through 0002
    on its way to 2026: neither the bounds nor the filtering may interrupt the typing. Day and
    month are the same so the test holds in either segment order."""
    page.goto(f"{live_server.url}/evenements/")
    page.get_by_role("button", name="Date").click()
    expect(page.get_by_label("À partir du")).to_be_visible()

    page.get_by_label("À partir du").press_sequentially("11112026")
    page.get_by_label("Jusqu'au").press_sequentially("12122026")

    expect(page.get_by_label("À partir du")).to_have_value("2026-11-11")
    expect(page.get_by_label("Jusqu'au")).to_have_value("2026-12-12")
    expect(page).to_have_url(re.compile("date_from=2026-11-11&date_to=2026-12-12"))


def test_resetting_brings_every_filter_back_to_its_default(page, live_server):
    page.goto(f"{live_server.url}/evenements/")
    reset = page.get_by_role("button", name="Tout réinitialiser")
    expect(reset).to_be_hidden()

    location_type = page.get_by_role("button", name="En ligne / en présentiel")
    location_type.click()
    _click_label_of(page.get_by_role("switch", name="En ligne"))
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Type d'événement").click()
    _click_label_of(page.get_by_role("checkbox", name="Atelier"))
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Date").click()
    page.get_by_label("À partir du").fill("2026-09-14")
    page.keyboard.press("Escape")
    _click_label_of(page.get_by_role("switch", name="Gratuit uniquement"))

    expect(reset).to_be_visible()
    reset.click()

    expect(reset).to_be_hidden()
    expect(location_type).to_be_focused()
    expect(page.get_by_role("button", name="Retirer le filtre Atelier")).not_to_be_attached()
    expect(page.get_by_role("switch", name="Gratuit uniquement")).not_to_be_checked()
    location_type.click()
    expect(page.get_by_role("switch", name="En ligne")).not_to_be_checked()
    expect(page.get_by_role("switch", name="En présentiel")).not_to_be_checked()
    page.get_by_role("button", name="Type d'événement").click()
    expect(page.get_by_role("checkbox", name="Atelier")).not_to_be_checked()
    page.get_by_role("button", name="Date").click()
    expect(page.get_by_label("À partir du")).to_have_value("")


def test_ticking_online_disables_and_clears_the_place_filter(page, live_server):
    page.goto(f"{live_server.url}/evenements/")
    place = page.get_by_role("button", name="Région / Département")
    place.click()
    page.get_by_label("Rechercher une région ou un département").fill("Finistère")
    _click_label_of(page.get_by_role("checkbox", name="Finistère (29)"))
    page.keyboard.press("Escape")
    remove = page.get_by_role("button", name="Retirer le filtre Finistère (29)")
    expect(remove).to_be_attached()

    page.get_by_role("button", name="En ligne / en présentiel").click()
    _click_label_of(page.get_by_role("switch", name="En ligne"))

    expect(place).to_be_disabled()
    expect(remove).not_to_be_attached()

    _click_label_of(page.get_by_role("switch", name="En présentiel"))

    expect(place).to_be_enabled()
    expect(place).not_to_have_attribute("aria-describedby", re.compile("."))


def test_the_disabled_place_filter_explains_itself_to_the_keyboard_and_stays_shut(
    page, live_server
):
    page.goto(f"{live_server.url}/evenements/?location_type=online")
    place = page.get_by_role("button", name="Région / Département")

    place.focus()
    expect(place).to_be_focused()
    expect(place).to_have_accessible_description(PLACE_DISABLED_REASON)
    expect(page.get_by_role("tooltip")).to_have_text(PLACE_DISABLED_REASON)

    page.keyboard.press("Escape")
    expect(page.get_by_role("tooltip")).to_be_hidden()

    place.click(force=True)
    expect(place).to_have_attribute("aria-expanded", "false")


def test_the_disabled_place_filter_explains_itself_on_hover(page, live_server):
    page.goto(f"{live_server.url}/evenements/?location_type=online")

    page.get_by_role("button", name="Région / Département").hover()

    tooltip = page.get_by_role("tooltip")
    expect(tooltip).to_have_text(PLACE_DISABLED_REASON)
    tooltip.hover()
    expect(tooltip).to_be_visible()


def test_a_url_online_only_opens_with_the_place_filter_disabled(page, live_server):
    page.goto(f"{live_server.url}/evenements/?location_type=online")

    expect(page.get_by_role("button", name="Région / Département")).to_be_disabled()


def test_switching_a_filter_narrows_the_list_without_reloading_the_page(page, live_server, pro):
    save_onsite_event(pro, "Salon à Brest", "29019")
    approved_event(pro, title="Webinaire").save()
    page.goto(f"{live_server.url}/evenements/")
    location_type = page.get_by_role("button", name="En ligne / en présentiel")
    location_type.click()

    _click_label_of(page.get_by_role("switch", name="En ligne"))

    expect(page.locator("#event_count")).to_have_text("1\xa0événement")
    expect(page.get_by_text("Salon à Brest")).to_be_hidden()
    expect(page.get_by_role("switch", name="En présentiel")).to_be_visible()
    expect(page).to_have_url(re.compile(r"location_type=online"))

    page.keyboard.press("Escape")
    page.get_by_role("button", name="Tout réinitialiser").click()

    expect(page.locator("#event_count")).to_have_text("2\xa0événements")


def test_the_empty_state_link_resets_the_filters_without_reloading_the_page(
    page, live_server, pro
):
    approved_event(pro, title="Webinaire").save()
    page.goto(f"{live_server.url}/evenements/?location_type=physical")
    page.evaluate("window.notReloaded = true")

    page.get_by_role("link", name="Réinitialiser la recherche").click()

    expect(page.locator("#event_count")).to_have_text("1\xa0événement")
    expect(page.get_by_role("button", name="En ligne / en présentiel")).to_be_focused()
    assert page.evaluate("window.notReloaded")


def test_ticking_online_drops_the_departments_from_the_url(page, live_server):
    page.goto(f"{live_server.url}/evenements/?department=29")
    page.get_by_role("button", name="En ligne / en présentiel").click()

    _click_label_of(page.get_by_role("switch", name="En ligne"))

    expect(page).to_have_url(re.compile(r"location_type=online"))
    assert "department=" not in page.url


def test_ticking_a_location_type_unticks_the_other_and_names_the_filter(page, live_server):
    page.goto(f"{live_server.url}/evenements/")
    location_type = page.get_by_role("button", name="En ligne / en présentiel")
    location_type.click()
    online = page.get_by_role("switch", name="En ligne")
    onsite = page.get_by_role("switch", name="En présentiel")

    _click_label_of(online)
    _click_label_of(onsite)

    expect(online).not_to_be_checked()
    expect(onsite).to_be_checked()
    expect(location_type).to_have_accessible_name(
        "En ligne / en présentiel\xa0: En présentiel uniquement"
    )
    expect(page.get_by_role("button", name="Retirer le filtre")).to_have_count(1)
    expect(page).to_have_url(re.compile(r"[?&]location_type=physical&"))

    _click_label_of(onsite)

    expect(location_type).to_have_accessible_name("En ligne / en présentiel")
    expect(page.get_by_role("button", name="Retirer le filtre")).to_have_count(0)


def test_a_filtered_url_opens_with_the_location_type_and_the_dates_named(page, live_server):
    page.goto(
        f"{live_server.url}/evenements/?location_type=physical"
        "&date_from=2026-09-14&date_to=2026-10-31"
    )

    expect(page.get_by_role("button", name="En ligne / en présentiel")).to_have_accessible_name(
        "En ligne / en présentiel\xa0: En présentiel uniquement"
    )
    expect(page.get_by_role("button", name="Date")).to_have_accessible_name(
        "Date\xa0: du 14/09/26 au 31/10/26"
    )


def test_removing_the_location_type_from_the_selected_filters_unnames_the_filter(
    page, live_server
):
    page.goto(f"{live_server.url}/evenements/?location_type=physical")

    page.get_by_role("button", name="Retirer le filtre En présentiel uniquement").click()

    expect(page.get_by_role("button", name="En ligne / en présentiel")).to_have_accessible_name(
        "En ligne / en présentiel"
    )
    expect(page.get_by_text("Filtres sélectionnés")).to_be_hidden()


def _click_label_of(control):
    """The input itself is visually hidden behind its drawn tick or switch: the label is what
    she clicks."""
    control.page.locator("label").filter(has=control).click()


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


def test_saving_from_the_participation_modal_syncs_the_bookmarks_behind_it(
    page, live_server, beneficiary, event
):
    """The detail page carries one bookmark per breakpoint and the modal opens a third: a
    toggle in any of them has to leave the others saying the same thing."""
    event.status = Event.Status.APPROVED
    event.access_type = Event.AccessType.REGISTRATION
    event.registration_url = "https://example.com/inscription"
    event.save()
    page.goto(f"{live_server.url}/se-connecter/token/{beneficiary.issue_login_token()}/")
    page.goto(f"{live_server.url}/evenements/{event.slug}/")
    page.get_by_role("button", name="Participer").click()
    bookmarks = page.locator(f'[data-bookmark="{event.pk}"]')
    expect(bookmarks.locator('[aria-pressed="false"]')).to_have_count(3)

    page.locator("dialog").get_by_label("Enregistrer cet événement").click()

    expect(bookmarks.locator('[aria-pressed="true"]')).to_have_count(3)


def test_an_event_saved_from_its_card_is_saved_on_its_page_and_back(
    page, live_server, beneficiary, event
):
    """Going back or forward must not bring a page back from the browser cache, holding the
    bookmark as it was before the last toggle."""
    event.status = Event.Status.APPROVED
    event.save()
    page.goto(f"{live_server.url}/se-connecter/token/{beneficiary.issue_login_token()}/")
    page.goto(f"{live_server.url}/evenements/")
    page.get_by_role("button", name="Enregistrer cet événement").click()
    expect(page.locator('[data-bookmark] [aria-pressed="true"]')).to_have_count(1)
    page.get_by_role("link", name=f"Voir l'événement {event.title}").dispatch_event("click")
    expect(page.locator('[data-bookmark] [aria-pressed="true"]')).to_have_count(2)

    page.go_back()

    expect(page.locator('[data-bookmark] [aria-pressed="true"]')).to_have_count(1)

    page.get_by_role("button", name="Retirer cet événement de mes favoris").click()
    expect(page.locator('[data-bookmark] [aria-pressed="false"]')).to_have_count(1)
    page.go_forward()

    expect(page.locator('[data-bookmark] [aria-pressed="false"]')).to_have_count(2)


def test_searching_narrows_the_list_and_reveals_the_sort(page, live_server, pro):
    today = timezone.localdate()
    for title, days, description in [
        ("Réseaux et sécurité", 5, "Un peu de web"),
        ("Atelier web", 30, ""),
        ("Atelier design", 5, ""),
    ]:
        start = today + timedelta(days=days)
        approved_event(
            pro, title=title, description=description, start_date=start, end_date=start
        ).save()
    page.goto(f"{live_server.url}/evenements/")
    sort = page.get_by_role("button", name="Trier par")
    first_title = page.locator("#event_results h2").first
    expect(sort).to_be_hidden()

    page.get_by_label("Rechercher un événement").fill("web")
    page.get_by_role("button", name="Rechercher").click()

    expect(page.locator("#event_count")).to_have_text("2\xa0événements")
    expect(sort).to_have_text("pertinence")
    expect(first_title).to_have_text("Atelier web")

    sort.click()
    page.get_by_role("group", name="Trier par").get_by_text("Date").click()

    expect(page).to_have_url(re.compile("sort=date"))
    expect(first_title).to_have_text("Réseaux et sécurité")
    expect(sort).to_have_text("date")


def test_a_too_short_search_shows_an_error(page, live_server):
    page.goto(f"{live_server.url}/evenements/")
    search = page.get_by_label("Rechercher un événement")

    search.fill("w")
    search.press("Enter")

    expect(
        page.get_by_role("alert").filter(has_text="Saisis au moins 2 caractères")
    ).to_be_visible()
    expect(search).to_have_attribute("aria-invalid", "true")
