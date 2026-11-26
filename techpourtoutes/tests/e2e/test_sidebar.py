import pytest
from playwright.sync_api import expect

IN_MENU = "document.activeElement.closest('nav[aria-label=\"Menu principal\"]') !== null"
IN_PAGE = "document.activeElement.closest('.drawer-content, #messages, [href=\"#contenu\"]')"
ON_BURGER = "document.activeElement.id === 'sidebar-drawer'"


@pytest.fixture
def desktop_page(browser):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    yield context.new_page()
    context.close()


@pytest.fixture
def mobile_page(browser):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    yield context.new_page()
    context.close()


@pytest.fixture
def landscape_page(browser):
    context = browser.new_context(viewport={"width": 844, "height": 390})
    yield context.new_page()
    context.close()


def _open_menu(page, live_server):
    page.goto(live_server.url)
    burger = page.get_by_role("checkbox", name="Menu")
    burger.focus()
    page.keyboard.press("Space")
    expect(page.get_by_role("navigation", name="Menu principal")).to_be_visible()
    return burger


def test_the_header_then_the_menu_come_right_after_the_skip_link_on_a_wide_screen(
    desktop_page, live_server
):
    desktop_page.goto(live_server.url)

    desktop_page.keyboard.press("Tab")
    expect(desktop_page.get_by_role("link", name="Aller au contenu")).to_be_focused()
    desktop_page.keyboard.press("Tab")
    expect(
        desktop_page.get_by_role("banner").get_by_role(
            "link", name="Accueil TechPourToutes Programme"
        )
    ).to_be_focused()
    desktop_page.keyboard.press("Tab")
    assert desktop_page.evaluate(IN_MENU)


def test_the_burger_leads_into_the_menu(mobile_page, live_server):
    _open_menu(mobile_page, live_server)

    mobile_page.keyboard.press("Tab")
    assert mobile_page.evaluate(IN_MENU)


def test_the_open_menu_keeps_the_focus_away_from_the_page(mobile_page, live_server):
    burger = _open_menu(mobile_page, live_server)

    focused_burger_again = False
    for _ in range(30):
        mobile_page.keyboard.press("Tab")
        assert not mobile_page.evaluate(IN_PAGE)
        focused_burger_again |= mobile_page.evaluate(ON_BURGER)
    assert focused_burger_again
    expect(burger).to_be_checked()


def test_escape_closes_the_menu_and_gives_the_focus_back_to_the_burger(mobile_page, live_server):
    burger = _open_menu(mobile_page, live_server)
    mobile_page.keyboard.press("Tab")

    mobile_page.keyboard.press("Escape")
    expect(burger).not_to_be_checked()
    expect(burger).to_be_focused()


def test_a_short_screen_scrolls_the_whole_menu_over_the_header(landscape_page, live_server):
    _open_menu(landscape_page, live_server)
    last_link = landscape_page.get_by_role("link", name="S'engager")

    expect(last_link).not_to_be_in_viewport()
    last_link.scroll_into_view_if_needed()
    expect(last_link).to_be_in_viewport()
    # inert content is left out of hit-testing: lift it to see what is painted on top
    landscape_page.evaluate("document.querySelector('.drawer-content').inert = false")
    assert landscape_page.evaluate(
        "document.elementFromPoint(20, 20).closest('nav[aria-label=\"Menu principal\"]')"
    )
