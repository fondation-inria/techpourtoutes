import re
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import expect
from waffle.testutils import override_switch

from techpourtoutes.models import JobPosting

from ..views.test_beneficiary_views import save_job_posting

# The filters only come alive once the page runs: a view test sees the checkboxes in the
# markup, not that ticking one keeps the panel open, counts it and lists it below.


@override_switch("internships", active=True)
def test_a_ticked_filter_is_counted_and_listed_until_removed(page, live_server):
    for index in range(3):
        save_job_posting(f"Stage {index}", JobPosting.Category.HIGHER_ED_INTERNSHIP)
    page.goto(f"{live_server.url}/stages-alternances-emplois/")

    domain = page.get_by_role("button", name="Domaine")
    domain.click()
    page.get_by_text("Électronique", exact=True).click()

    expect(page.get_by_role("checkbox", name="Électronique")).to_be_checked()
    expect(page.get_by_role("checkbox", name="Électrotechnique")).to_be_visible()
    expect(domain).to_contain_text("1")
    expect(page.get_by_role("list", name="Domaine").get_by_role("listitem")).to_have_count(1)

    page.keyboard.press("Escape")
    page.get_by_role("button", name="Retirer le filtre Électronique").click()

    expect(page.get_by_text("Filtres sélectionnés")).to_be_hidden()
    expect(domain).not_to_contain_text("1")


@override_switch("internships", active=True)
def test_a_ticked_region_stands_for_its_departments_until_one_is_unticked(page, live_server):
    page.goto(f"{live_server.url}/stages-alternances-emplois/")
    location = page.get_by_role("button", name="Région / Département")
    location.click()

    page.get_by_text("Bretagne", exact=True).click()

    expect(page.get_by_role("button", name="Retirer le filtre Bretagne")).to_be_attached()
    expect(location).to_contain_text("1")

    page.get_by_role("button", name="Départements de Bretagne").click()
    expect(page.get_by_role("checkbox", name="Finistère (29)")).to_be_checked()
    page.get_by_text("Finistère (29)", exact=True).click()

    expect(page.get_by_role("button", name="Retirer le filtre Bretagne")).not_to_be_attached()
    expect(page.get_by_role("button", name="Retirer le filtre Morbihan (56)")).to_be_attached()
    expect(location).to_contain_text("3")
    assert page.get_by_role("checkbox", name="Bretagne").evaluate("box => box.indeterminate")


@override_switch("internships", active=True)
def test_resetting_unticks_every_filter_at_once(page, live_server):
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    save_job_posting("Stage web", category)
    save_job_posting("Stage en design", category)
    page.goto(f"{live_server.url}/stages-alternances-emplois/?q=web&sort=date")
    expect(page.locator("#job_posting_count")).to_have_text("1\xa0offre")
    location = page.get_by_role("button", name="Région / Département")
    location.click()
    page.get_by_role("button", name="Départements de Bretagne").click()
    page.get_by_text("Finistère (29)", exact=True).click()
    domain = page.get_by_role("button", name="Domaine")
    domain.click()
    page.get_by_text("Électronique", exact=True).click()
    page.keyboard.press("Escape")

    page.get_by_role("button", name="Tout réinitialiser").click()

    expect(page.get_by_text("Filtres sélectionnés")).to_be_hidden()
    expect(location).not_to_contain_text("1")
    expect(domain).not_to_contain_text("1")
    expect(location).to_be_focused()
    finistere = page.get_by_role("checkbox", name="Finistère (29)", include_hidden=True)
    expect(finistere).not_to_be_checked()
    bretagne = page.get_by_role("checkbox", name="Bretagne", include_hidden=True)
    assert not bretagne.evaluate("box => box.indeterminate")
    expect(page.get_by_label("Rechercher une offre")).to_have_value("")
    expect(page.locator("#job_posting_count")).to_have_text("2\xa0offres")
    expect(page.get_by_role("button", name="Trier par")).to_be_hidden()
    assert "q=web" not in page.url
    assert "sort=date" not in page.url


@override_switch("internships", active=True)
def test_resetting_brings_back_the_duration_filter_a_lone_cdi_took_away(page, live_server):
    page.goto(f"{live_server.url}/stages-alternances-emplois/?category=first_job")
    duration = page.get_by_role("button", name="Durée")
    page.get_by_role("button", name="Type de contrat").click()
    page.locator("#job_posting_contract_type_panel").get_by_text("CDI", exact=True).click()
    expect(duration).to_be_hidden()
    page.keyboard.press("Escape")

    page.get_by_role("button", name="Tout réinitialiser").click()

    expect(duration).to_be_visible()


@override_switch("internships", active=True)
def test_ticking_a_filter_narrows_the_list_without_reloading_the_page(page, live_server):
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    save_job_posting("Stage à Brest", category, department_code="29")
    save_job_posting(
        "Stage de maths à Brest", category, department_code="29", domains=["mathematiques"]
    )
    save_job_posting("Stage à Rennes", category, department_code="35")
    page.goto(f"{live_server.url}/stages-alternances-emplois/")
    location = page.get_by_role("button", name="Région / Département")
    location.click()
    page.get_by_role("button", name="Départements de Bretagne").click()

    page.get_by_text("Finistère (29)", exact=True).click()

    expect(page.locator("#job_posting_count")).to_have_text("2\xa0offres")
    expect(page.get_by_text("Stage à Rennes")).to_be_hidden()
    expect(location).to_be_visible()
    expect(page.get_by_role("checkbox", name="Morbihan (56)")).to_be_visible()
    assert "department=29" in page.url

    page.keyboard.press("Escape")
    page.get_by_role("button", name="Domaine").click()
    page.locator("#job_posting_domain_panel").get_by_text("Mathématiques", exact=True).click()

    expect(page.locator("#job_posting_count")).to_have_text("1\xa0offre")

    page.keyboard.press("Escape")
    page.get_by_role("button", name="Retirer le filtre Finistère (29)").click()
    page.get_by_role("button", name="Retirer le filtre Mathématiques").click()

    expect(page.locator("#job_posting_count")).to_have_text("3\xa0offres")


@override_switch("internships", active=True)
def test_going_back_shows_the_filters_of_the_previous_url(page, live_server):
    page.goto(f"{live_server.url}/stages-alternances-emplois/")
    page.get_by_role("button", name="Domaine").click()
    panel = page.locator("#job_posting_domain_panel")
    panel.get_by_text("Électronique", exact=True).click()
    expect(page).to_have_url(re.compile("domain=electronique$"))
    panel.get_by_text("Mathématiques", exact=True).click()
    expect(page).to_have_url(re.compile("domain=mathematiques$"))

    page.go_back()

    expect(page.get_by_role("list", name="Domaine").get_by_role("listitem")).to_have_count(1)
    electronique = page.get_by_role("checkbox", name="Électronique", include_hidden=True)
    expect(electronique).to_be_checked()


@override_switch("internships", active=True)
def test_a_filtered_url_opens_with_its_filters_ticked(page, live_server):
    page.goto(f"{live_server.url}/stages-alternances-emplois/?department=29&domain=mathematiques")

    expect(page.get_by_role("button", name="Retirer le filtre Finistère (29)")).to_be_visible()
    expect(page.get_by_role("button", name="Retirer le filtre Mathématiques")).to_be_visible()
    expect(page.get_by_role("button", name="Région / Département")).to_contain_text("1")
    bretagne = page.get_by_role("checkbox", name="Bretagne", include_hidden=True)
    assert bretagne.evaluate("box => box.indeterminate")


@override_switch("internships", active=True)
def test_searching_a_place_shows_the_matches_under_their_region(page, live_server):
    page.goto(f"{live_server.url}/stages-alternances-emplois/")
    page.get_by_role("button", name="Région / Département").click()
    search = page.get_by_label("Rechercher une région ou un département")

    search.fill("finis")

    expect(page.get_by_text("Bretagne", exact=True)).to_be_visible()
    expect(page.get_by_text("Finistère (29)", exact=True)).to_be_visible()
    expect(page.get_by_text("Morbihan (56)", exact=True)).to_be_hidden()
    expect(page.get_by_text("Normandie", exact=True)).to_be_hidden()

    search.fill("bretagne")

    expect(page.get_by_text("Morbihan (56)", exact=True)).to_be_visible()

    search.fill("ile de france")

    expect(page.get_by_text("Paris (75)", exact=True)).to_be_visible()

    search.fill("2A")

    expect(page.get_by_text("Corse-du-Sud (2A)", exact=True)).to_be_visible()


@override_switch("internships", active=True)
def test_back_from_a_posting_returns_where_she_was_in_the_listing(page, live_server):
    for index in range(20):
        save_job_posting(f"Stage {index}", JobPosting.Category.APPRENTICESHIP)
    page.goto(f"{live_server.url}/stages-alternances-emplois/?category=apprenticeship")
    page.get_by_role("button", name="Domaine").click()
    page.locator("#job_posting_domain_panel").get_by_text(
        "Développement - programmation - logiciel", exact=True
    ).click()
    expect(page).to_have_url(re.compile(r"domain=developpement"))
    listing = page.url
    page.keyboard.press("Escape")
    last_card = page.get_by_role("link", name="Stage 0", exact=True)
    last_card.scroll_into_view_if_needed()
    scrolled = page.evaluate("window.scrollY")
    assert scrolled > 0

    last_card.click()
    page.get_by_role("link", name="Retour").click()

    expect(page).to_have_url(listing)
    page.wait_for_function(f"Math.abs(window.scrollY - {scrolled}) < 2")


@override_switch("internships", active=True)
def test_searching_narrows_the_list_and_reveals_the_sort_which_keeps_the_focus(page, live_server):
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    now = timezone.now()
    save_job_posting("Stage web", category, published_at=now - timedelta(days=5))
    save_job_posting("Stage en réseaux", category, description="Un peu de web", published_at=now)
    save_job_posting("Stage en design", category)
    page.goto(f"{live_server.url}/stages-alternances-emplois/")
    sort = page.get_by_role("button", name="Trier par")
    options = page.get_by_role("group", name="Trier par")
    expect(sort).to_be_hidden()

    page.get_by_label("Rechercher une offre").fill("web")
    page.get_by_role("button", name="Rechercher").click()

    expect(page.locator("#job_posting_count")).to_have_text("2\xa0offres")
    expect(sort).to_have_text("pertinence")
    first_title = page.locator("#job_posting_results h3").first
    expect(first_title).to_have_text("Stage web")
    expect(options).to_be_hidden()

    sort.click()
    expect(options.get_by_role("radio", name="Pertinence")).to_be_checked()
    page.keyboard.press("Escape")
    expect(options).to_be_hidden()
    expect(sort).to_be_focused()

    sort.click()
    options.get_by_text("Date").click(delay=120)

    expect(page).to_have_url(re.compile("sort=date"))
    expect(first_title).to_have_text("Stage en réseaux")
    expect(sort).to_have_text("date")
    expect(options).to_be_hidden()
    expect(sort).to_be_focused()

    page.keyboard.press("Enter")
    expect(options).to_be_visible()
    page.keyboard.press("Tab")
    page.keyboard.press("ArrowUp")

    expect(first_title).to_have_text("Stage web")
    expect(sort).to_have_text("pertinence")
    expect(options).to_be_hidden()
    expect(sort).to_be_focused()

    page.get_by_label("Rechercher une offre").fill("")
    page.keyboard.press("Enter")

    expect(page.locator("#job_posting_count")).to_have_text("3\xa0offres")
    expect(sort).to_be_hidden()


@override_switch("internships", active=True)
def test_the_search_cross_clears_the_search_and_gives_the_focus_back(page, live_server):
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    save_job_posting("Stage web", category)
    save_job_posting("Stage en design", category)
    page.goto(f"{live_server.url}/stages-alternances-emplois/?q=web")
    search = page.get_by_label("Rechercher une offre")
    clear = page.get_by_role("button", name="Effacer la recherche")
    count = page.locator("#job_posting_count")

    clear.click()

    expect(search).to_have_value("")
    expect(count).to_have_text("2\xa0offres")
    expect(search).to_be_focused()
    expect(clear).to_be_hidden()

    search.fill("web")
    search.press("Enter")

    expect(count).to_have_text("1\xa0offre")
    clear.click()

    expect(search).to_have_value("")
    expect(count).to_have_text("2\xa0offres")
    expect(search).to_be_focused()


@override_switch("internships", active=True)
def test_the_search_cross_sends_nothing_when_no_search_was_made(page, live_server):
    page.goto(f"{live_server.url}/stages-alternances-emplois/")
    search = page.get_by_label("Rechercher une offre")
    urls = []
    page.on("request", lambda request: urls.append(request.url))

    search.fill("web")
    page.get_by_role("button", name="Effacer la recherche").click()

    expect(search).to_have_value("")
    page.wait_for_timeout(200)
    assert [url for url in urls if "stages-alternances" in url] == []


@override_switch("internships", active=True)
def test_resetting_the_search_clears_the_filters_and_the_text_and_shows_every_posting(
    page, live_server
):
    category = JobPosting.Category.APPRENTICESHIP
    save_job_posting("Alternance web", category)
    save_job_posting("Alternance design", category)
    save_job_posting("Stage web", JobPosting.Category.HIGHER_ED_INTERNSHIP)
    page.goto(f"{live_server.url}/stages-alternances-emplois/?category=apprenticeship")
    search = page.get_by_label("Rechercher une offre")
    page.get_by_role("button", name="Domaine").click()
    page.locator("#job_posting_domain_panel").get_by_text("Électronique", exact=True).click()
    expect(page.locator("#job_posting_count")).to_have_text("0\xa0offre")
    page.keyboard.press("Escape")
    search.fill("introuvable")
    search.press("Enter")
    expect(page).to_have_url(re.compile("q=introuvable"))

    page.get_by_role("link", name="Réinitialiser la recherche").click()

    expect(page.locator("#job_posting_count")).to_have_text("2\xa0offres")
    expect(page.get_by_text("Filtres sélectionnés")).to_be_hidden()
    expect(page.get_by_role("button", name="Domaine")).not_to_contain_text("1")
    expect(search).to_have_value("")
    expect(page.get_by_role("button", name="Région / Département")).to_be_focused()
    assert "category=apprenticeship" in page.url
    assert "q=introuvable" not in page.url
    assert "domain=" not in page.url


@override_switch("internships", active=True)
def test_the_reset_button_shows_once_a_search_is_launched_without_the_filters_label(
    page, live_server
):
    page.goto(f"{live_server.url}/stages-alternances-emplois/")
    reset = page.get_by_role("button", name="Tout réinitialiser")
    search = page.get_by_label("Rechercher une offre")
    expect(reset).to_be_hidden()

    search.fill("web")

    expect(reset).to_be_hidden()

    page.get_by_role("button", name="Rechercher").click()

    expect(reset).to_be_visible()
    expect(page.get_by_text("Filtres sélectionnés")).to_be_hidden()
    search_box = page.get_by_role("button", name="Rechercher").bounding_box()
    reset_box = reset.bounding_box()
    assert search_box["y"] <= reset_box["y"] <= search_box["y"] + search_box["height"]

    page.get_by_role("button", name="Effacer la recherche").click()

    expect(reset).to_be_hidden()

    page.get_by_role("button", name="Domaine").click()
    page.locator("#job_posting_domain_panel").get_by_text("Électronique", exact=True).click()

    expect(reset).to_be_visible()
    expect(page.get_by_text("Filtres sélectionnés")).to_be_visible()

    page.keyboard.press("Escape")
    page.get_by_role("button", name="Retirer le filtre Électronique").click()

    expect(reset).to_be_hidden()


@override_switch("internships", active=True)
def test_a_too_short_search_shows_an_error_and_still_filters(page, live_server):
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    save_job_posting("Stage de maths", category, domains=["mathematiques"])
    save_job_posting("Stage web", category)
    page.goto(f"{live_server.url}/stages-alternances-emplois/")
    search = page.get_by_label("Rechercher une offre")
    error = page.get_by_role("alert").filter(has_text="Saisis au moins 2 caractères")

    search.fill("w")
    search.press("Enter")

    expect(error).to_be_visible()
    expect(page.locator("#job_posting_count")).to_have_text("2\xa0offres")
    expect(search).to_be_focused()
    expect(search).to_have_attribute("aria-invalid", "true")
    expect(search).to_have_accessible_description(re.compile("Saisis au moins 2 caractères"))

    page.get_by_role("button", name="Domaine").click()
    page.locator("#job_posting_domain_panel").get_by_text("Mathématiques", exact=True).click()

    expect(page.locator("#job_posting_count")).to_have_text("1\xa0offre")
    expect(error).to_be_visible()

    page.keyboard.press("Escape")
    search.fill("web")
    search.press("Enter")

    expect(error).to_be_hidden()
    expect(search).not_to_have_attribute("aria-invalid", "true")
    expect(search).to_be_focused()


def _save_posting_with_three_domains():
    return save_job_posting(
        "Stage",
        JobPosting.Category.HIGHER_ED_INTERNSHIP,
        domains=[
            JobPosting.Domain.DEVELOPPEMENT,
            JobPosting.Domain.MATHEMATIQUES,
            JobPosting.Domain.SYSTEMES_ET_RESEAUX,
        ],
    )


@override_switch("internships", active=True)
def test_clicking_the_stacked_domains_unfolds_them_and_reduire_folds_them_back(page, live_server):
    job_posting = _save_posting_with_three_domains()
    page.goto(f"{live_server.url}{reverse('show_job_posting', args=[job_posting.pk])}")
    stack = page.get_by_role("button", name=re.compile("\\+2 autres domaines"))
    maths = page.get_by_text("Mathématiques", exact=True)
    expect(maths).to_be_hidden()

    # Its centre is the first badge, not the counter in the corner.
    stack.click()

    expect(maths).to_be_visible()
    expect(page.get_by_text("Systèmes et réseaux", exact=True)).to_be_visible()
    expect(stack).to_be_hidden()

    page.get_by_role("button", name="Réduire").click()

    expect(maths).to_be_hidden()
    expect(stack).to_be_visible()


@override_switch("internships", active=True)
def test_unfolding_the_domains_from_the_keyboard_moves_the_focus_to_reduire(page, live_server):
    job_posting = _save_posting_with_three_domains()
    page.goto(f"{live_server.url}{reverse('show_job_posting', args=[job_posting.pk])}")
    stack = page.get_by_role("button", name=re.compile("\\+2 autres domaines"))
    stack.focus()

    page.keyboard.press("Enter")

    expect(page.get_by_role("button", name="Réduire")).to_be_focused()

    page.keyboard.press("Enter")

    expect(stack).to_be_focused()
