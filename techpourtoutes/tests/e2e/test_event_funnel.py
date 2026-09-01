import pytest
from django.core import mail
from django.test import override_settings
from playwright.sync_api import expect

from techpourtoutes.models import Event, Pro

# These tests drive a real browser to cover what the view tests cannot: every conditional field
# of this funnel is revealed client-side, and the answers only exist in the page — a step is
# submitted with hidden inputs the previous screen rendered.

locmem = override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    NEW_EVENT_RECIPIENTS=["agir@techpourtoutes.io"],
)


@pytest.fixture
def funnel(live_server, page, db):
    pro = Pro(
        username="alice@example.com",
        civility=Pro.Civility.MADAME,
        first_name="Alice",
        last_name="Martin",
        email="alice@example.com",
        professional_situation=Pro.ProfessionalSituation.WORKING,
    )
    pro.save()
    page.goto(f"{live_server.url}/se-connecter/token/{pro.issue_login_token()}/")
    page.goto(f"{live_server.url}/coalition/proposer-un-evenement/")
    return page


def choose_subcategory(page, option):
    page.get_by_label("Quel type d'événement voulez-vous proposer ?").click()
    page.get_by_role("button", name=option, exact=True).click()


def fill_details(page):
    page.get_by_label("Nom de l'organisateur*").fill("Numeum")
    page.get_by_label("Nom de l'événement*").fill("Salon des métiers du numérique")
    page.get_by_label("Description de l'événement*").fill("Une journée de rencontres.")
    page.get_by_label("Date de début*").fill("2026-10-01")
    page.get_by_label("Heure de début*").fill("09:00")


def test_the_end_date_follows_the_start_date_until_she_changes_it(funnel):
    choose_subcategory(funnel, "Salon")
    funnel.get_by_role("button", name="Continuer").click()
    fill_details(funnel)

    expect(funnel.get_by_label("Date de fin*")).to_have_value("2026-10-01")

    funnel.get_by_label("Date de fin*").fill("2026-10-03")
    funnel.get_by_label("Date de début*").fill("2026-10-02")
    expect(funnel.get_by_label("Date de fin*")).to_have_value("2026-10-03")


def test_the_other_subcategory_reveals_its_free_text_field(funnel):
    free_text = funnel.get_by_label("Veuillez préciser le type d'événement")
    expect(free_text).to_be_hidden()

    choose_subcategory(funnel, "Autre")

    expect(free_text).to_be_visible()


def test_leaving_the_funnel_asks_for_confirmation(funnel):
    funnel.get_by_label("Fermer").click()

    expect(funnel.get_by_text("ne sera pas enregistré")).to_be_visible()
    funnel.get_by_role("button", name="Annuler").click()
    expect(funnel.get_by_text("ne sera pas enregistré")).to_be_hidden()


@locmem
def test_an_online_event_is_published_for_validation(funnel):
    choose_subcategory(funnel, "Webinaire d'informations")
    funnel.get_by_role("button", name="Continuer").click()
    fill_details(funnel)
    funnel.get_by_label("Heure de fin*").fill("18:00")
    funnel.get_by_role("button", name="Continuer").click()

    funnel.get_by_text("En ligne", exact=True).click()
    connection = funnel.get_by_label("Quel est le lien de connexion à l'événement ?")
    expect(connection).to_be_visible()
    connection.fill("https://example.org/live")
    funnel.get_by_text("Accès libre", exact=True).click()
    funnel.get_by_role("button", name="Publier").click()

    expect(funnel.get_by_text("en cours de validation")).to_be_visible()
    event = Event.objects.get()
    assert event.status == Event.Status.PENDING
    assert event.subcategory == "webinar"
    assert event.online_url == "https://example.org/live"
    assert len(mail.outbox) == 2


@locmem
def test_a_physical_event_is_geocoded_through_the_address_search(funnel, httpx_mock):
    httpx_mock.add_response(
        json={
            "features": [
                {
                    "properties": {
                        "id": "80021_6590_00008",
                        "label": "8 Boulevard du Port 80000 Amiens",
                        "name": "8 Boulevard du Port",
                        "postcode": "80000",
                        "city": "Amiens",
                        "citycode": "80021",
                    },
                    "geometry": {"coordinates": [2.290084, 49.897442]},
                }
            ]
        },
        is_reusable=True,
    )
    choose_subcategory(funnel, "Salon")
    funnel.get_by_role("button", name="Continuer").click()
    fill_details(funnel)
    funnel.get_by_label("Heure de fin*").fill("18:00")
    funnel.get_by_role("button", name="Continuer").click()

    funnel.get_by_text("En présentiel", exact=True).click()
    funnel.get_by_label("Quelle est l'adresse de l'événement ?*").fill("8 boulevard du port")
    funnel.get_by_role("option", name="8 Boulevard du Port 80000 Amiens").click()
    funnel.get_by_text("Accès libre", exact=True).click()
    funnel.get_by_role("button", name="Publier").click()

    expect(funnel.get_by_text("en cours de validation")).to_be_visible()
    event = Event.objects.get()
    assert event.city == "Amiens"
    assert event.latitude == 49.897442
    assert event.ban_id == "80021_6590_00008"


@locmem
def test_a_registration_link_is_demanded_only_when_registration_is_required(funnel):
    choose_subcategory(funnel, "Salon")
    funnel.get_by_role("button", name="Continuer").click()
    fill_details(funnel)
    funnel.get_by_label("Heure de fin*").fill("18:00")
    funnel.get_by_role("button", name="Continuer").click()

    expect(funnel.get_by_label("Lien d'inscription*")).to_be_hidden()
    funnel.get_by_text("Inscription obligatoire", exact=True).click()
    expect(funnel.get_by_label("Lien d'inscription*")).to_be_visible()

    funnel.get_by_text("Sur candidature", exact=True).click()
    expect(funnel.get_by_label("Lien de candidature*")).to_be_visible()
    expect(funnel.get_by_label("Lien d'inscription*")).to_be_hidden()


def test_a_paid_event_reveals_its_price(funnel):
    choose_subcategory(funnel, "Salon")
    funnel.get_by_role("button", name="Continuer").click()
    fill_details(funnel)
    funnel.get_by_label("Heure de fin*").fill("18:00")
    funnel.get_by_role("button", name="Continuer").click()

    expect(funnel.get_by_label("Tarif*")).to_be_hidden()
    funnel.get_by_role("button", name="Payant").click()
    expect(funnel.get_by_label("Tarif*")).to_be_visible()

    funnel.get_by_role("button", name="Gratuit").click()
    expect(funnel.get_by_label("Tarif*")).to_be_hidden()
