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
