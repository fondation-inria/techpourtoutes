import re
import struct
import zlib
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import expect

from techpourtoutes.models import Event, Pro

# These tests drive a real browser to cover what the view tests cannot: every conditional field
# of this funnel is revealed client-side, and the answers only exist in the page — a step is
# submitted with hidden inputs the previous screen rendered.

locmem = override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    NEW_EVENT_RECIPIENTS=["agir@techpourtoutes.io"],
)

START = timezone.localdate() + timedelta(days=30)


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
    page.get_by_label("Date de début*").fill(START.isoformat())
    page.get_by_label("Heure de début*").fill("09:00")


def test_the_end_date_follows_the_start_date_until_she_changes_it(funnel):
    choose_subcategory(funnel, "Salon")
    funnel.get_by_role("button", name="Continuer").click()
    fill_details(funnel)

    expect(funnel.get_by_label("Date de fin*")).to_have_value(START.isoformat())

    funnel.get_by_label("Date de fin*").fill("2026-10-03")
    funnel.get_by_label("Date de début*").fill("2026-10-02")
    expect(funnel.get_by_label("Date de fin*")).to_have_value("2026-10-03")


def test_the_end_date_follows_a_start_date_typed_digit_by_digit(funnel):
    """A date input fires `change` on every complete-looking state, so a year typed one digit
    at a time goes through 0002 before reaching 2026: the end date has to keep following."""
    choose_subcategory(funnel, "Salon")
    funnel.get_by_role("button", name="Continuer").click()
    funnel.get_by_label("Date de début*").press_sequentially("10122026")

    # The order of the segments follows the browser locale; the year is the same in both.
    start = funnel.get_by_label("Date de début*").input_value()
    assert start.startswith("2026-")
    expect(funnel.get_by_label("Date de fin*")).to_have_value(start)


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


@pytest.mark.parametrize(
    ("link_name", "destination"),
    [
        ("Accueil TechPourToutes Coalition", "/coalition/"),
        ("Mentions légales", "/mentions-legales/"),
    ],
)
def test_leaving_through_the_logo_or_the_footer_asks_for_confirmation_too(
    funnel, link_name, destination
):
    """Every way out of the page loses the answers, not only the close button: quitting then
    goes where the link pointed."""
    funnel.get_by_role("link", name=link_name).click()

    expect(funnel.get_by_text("ne sera pas enregistré")).to_be_visible()
    funnel.get_by_role("link", name="Quitter la création").click()
    expect(funnel).to_have_url(re.compile(f"{destination}$"))


@locmem
def test_leaving_a_submitted_event_closes_straight_away(funnel):
    """The confirmation is there to say the answers are about to be lost: once they are saved
    there is nothing left to warn about."""
    account_url = funnel.url.replace("/coalition/proposer-un-evenement/", "/mon-compte/")
    reach_the_location_step(funnel)
    funnel.get_by_text("En ligne", exact=True).click()
    funnel.get_by_role("button", name="Publier").click()
    expect(funnel.get_by_text("en cours de validation")).to_be_visible()

    funnel.get_by_label("Fermer").click()

    expect(funnel).to_have_url(account_url)


@locmem
def test_an_online_event_is_published_for_validation(funnel):
    choose_subcategory(funnel, "Webinaire d'info")
    funnel.get_by_role("button", name="Continuer").click()
    fill_details(funnel)
    funnel.get_by_label("Heure de fin*").fill("18:00")
    funnel.get_by_role("button", name="Continuer").click()

    funnel.get_by_text("En ligne", exact=True).click()
    connection = funnel.get_by_label("Quel est le lien de connexion à l'événement ?")
    expect(connection).to_be_visible()
    connection.fill("https://example.org/live")
    funnel.get_by_text("Sans inscription", exact=True).click()
    funnel.get_by_text("Gratuit", exact=True).click()
    funnel.get_by_role("button", name="Publier").click()

    expect(funnel.get_by_text("en cours de validation")).to_be_visible()
    event = Event.objects.get()
    assert event.status == Event.Status.PENDING
    assert event.subcategory == "webinar"
    assert event.online_url == "https://example.org/live"
    assert len(mail.outbox) == 2


@locmem
def test_a_physical_event_is_geocoded_through_the_address_search(funnel, mock_geocoding):
    mock_geocoding(
        addresses=[
            {
                "properties": {
                    "_type": "address",
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
    )
    choose_subcategory(funnel, "Salon")
    funnel.get_by_role("button", name="Continuer").click()
    fill_details(funnel)
    funnel.get_by_label("Heure de fin*").fill("18:00")
    funnel.get_by_role("button", name="Continuer").click()

    funnel.get_by_text("En présentiel", exact=True).click()
    funnel.get_by_label("Quelle est l'adresse ou le lieu de l'événement ?*").fill(
        "8 boulevard du port"
    )
    funnel.get_by_role("option", name="8 Boulevard du Port 80000 Amiens").click()
    funnel.get_by_text("Sans inscription", exact=True).click()
    funnel.get_by_text("Gratuit", exact=True).click()
    funnel.get_by_role("button", name="Publier").click()

    expect(funnel.get_by_text("en cours de validation")).to_be_visible()
    event = Event.objects.get()
    assert event.city == "Amiens"
    assert event.latitude == 49.897442
    assert event.ban_id == "80021_6590_00008"


@locmem
def test_a_venue_is_published_without_a_street_address(funnel, mock_geocoding):
    """A POI has no postal address, so the venue name and its commune are all we store."""
    mock_geocoding(
        pois=[
            {
                "properties": {
                    "_type": "poi",
                    "toponym": "Station F",
                    "postcode": ["75013"],
                    "city": ["Paris 13e Arrondissement", "Paris"],
                    "citycode": ["75113", "75056"],
                },
                "geometry": {"coordinates": [2.371699, 48.833436]},
            }
        ]
    )
    choose_subcategory(funnel, "Salon")
    funnel.get_by_role("button", name="Continuer").click()
    fill_details(funnel)
    funnel.get_by_label("Heure de fin*").fill("18:00")
    funnel.get_by_role("button", name="Continuer").click()

    funnel.get_by_text("En présentiel", exact=True).click()
    funnel.get_by_label("Quelle est l'adresse ou le lieu de l'événement ?*").fill("station f")
    funnel.get_by_role("option", name="Station F, Paris 13e Arrondissement").click()
    funnel.get_by_text("Sans inscription", exact=True).click()
    funnel.get_by_text("Gratuit", exact=True).click()
    funnel.get_by_role("button", name="Publier").click()

    expect(funnel.get_by_text("en cours de validation")).to_be_visible()
    event = Event.objects.get()
    assert event.poi_name == "Station F"
    assert event.address == ""
    assert event.city == "Paris 13e Arrondissement"
    assert event.latitude == 48.833436
    assert event.location_label == "Station F 75013 Paris 13e Arrondissement"


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
    funnel.get_by_text("Payant", exact=True).click()
    expect(funnel.get_by_label("Tarif*")).to_be_visible()

    funnel.get_by_text("Gratuit", exact=True).click()
    expect(funnel.get_by_label("Tarif*")).to_be_hidden()


def reach_the_location_step(page):
    choose_subcategory(page, "Salon")
    page.get_by_role("button", name="Continuer").click()
    fill_details(page)
    page.get_by_label("Heure de fin*").fill("18:00")
    page.get_by_role("button", name="Continuer").click()
    page.get_by_text("Sans inscription", exact=True).click()
    page.get_by_text("Gratuit", exact=True).click()


@locmem
def test_a_malformed_link_is_refused_by_the_page_not_by_the_browser(funnel):
    """A `type="url"` input would keep the submission from ever leaving the browser, behind a
    native bubble we cannot word."""
    reach_the_location_step(funnel)
    funnel.get_by_text("En ligne", exact=True).click()
    funnel.get_by_label("Quel est le lien de connexion à l'événement ?").fill("visio de la salle")
    funnel.get_by_role("button", name="Publier").click()

    expect(funnel.get_by_text("Saisissez un lien valide")).to_be_visible()


@locmem
def test_a_paid_event_without_a_price_comes_back_on_payant(funnel):
    """ "Payant" is an answer of its own, so it survives the round trip and the field the error
    is on stays visible."""
    reach_the_location_step(funnel)
    funnel.get_by_text("En ligne", exact=True).click()
    funnel.get_by_text("Payant", exact=True).click()
    funnel.get_by_role("button", name="Publier").click()

    expect(funnel.get_by_label("Tarif*")).to_be_visible()
    expect(funnel.get_by_text("Renseignez le tarif de l'événement.")).to_be_visible()


@locmem
def test_a_price_typed_in_words_is_refused_then_accepted_with_a_comma(funnel):
    reach_the_location_step(funnel)
    funnel.get_by_text("En ligne", exact=True).click()
    funnel.get_by_text("Payant", exact=True).click()
    funnel.get_by_label("Tarif*").fill("douze euros")
    funnel.get_by_role("button", name="Publier").click()

    expect(funnel.get_by_label("Tarif*")).to_be_visible()
    expect(funnel.get_by_text("Saisissez un nombre")).to_be_visible()

    funnel.get_by_label("Tarif*").fill("12,50")
    funnel.get_by_role("button", name="Publier").click()

    expect(funnel.get_by_text("en cours de validation")).to_be_visible()
    assert Event.objects.get().price == Decimal("12.50")


def reach_the_location_step_from(page, subcategory):
    choose_subcategory(page, subcategory)
    page.get_by_role("button", name="Continuer").click()
    fill_details(page)
    page.get_by_label("Heure de fin*").fill("18:00")
    page.get_by_role("button", name="Continuer").click()


def test_stepping_back_keeps_what_the_current_screen_already_holds(funnel):
    """Retour is a form of its own — a sibling, since HTML forbids nesting — so it has to pull
    the step's own fields in: without that, the answers on screen never reach the server and
    the step comes back blank."""
    reach_the_location_step_from(funnel, "Salon")
    funnel.get_by_text("En ligne", exact=True).click()
    funnel.get_by_text("Sans inscription", exact=True).click()
    funnel.get_by_text("Gratuit", exact=True).click()

    funnel.get_by_role("button", name="Retour").click()
    expect(funnel.get_by_label("Nom de l'événement*")).to_have_value(
        "Salon des métiers du numérique"
    )
    funnel.get_by_role("button", name="Continuer").click()

    # the connection link only shows while "En ligne" is the selected answer
    expect(funnel.get_by_label("Quel est le lien de connexion à l'événement ?")).to_be_visible()


@locmem
def test_an_event_is_edited_through_the_same_funnel(page, live_server, pro, event):
    event.status = Event.Status.APPROVED
    event.description = "Une journée pour rencontrer des professionnelles."
    event.save()
    page.goto(f"{live_server.url}/se-connecter/token/{pro.issue_login_token()}/")
    page.goto(f"{live_server.url}/coalition/evenements/{event.pk}/modifier/")

    expect(page.get_by_text("Modifier un événement")).to_be_visible()
    page.get_by_role("button", name="Continuer").click()
    page.get_by_role("button", name="Continuer").click()
    # the place is shown the way the search would have labelled it, commune included
    expect(page.get_by_text("8 Boulevard du Port 80000 Amiens")).to_be_visible()
    page.get_by_role("button", name="Retour").click()
    page.get_by_label("Nom de l'événement*").fill("Salon renommé")
    page.get_by_role("button", name="Continuer").click()
    page.get_by_role("button", name="Retour").click()
    page.get_by_role("button", name="Continuer").click()
    page.get_by_role("button", name="Publier", exact=True).click()

    expect(page.get_by_text("Voulez-vous modifier votre")).to_be_visible()
    page.get_by_role("button", name="Publier les modifications").click()

    expect(page).to_have_url(re.compile(rf"/evenements/{event.slug}/\?back="))
    event.refresh_from_db()
    assert event.title == "Salon renommé"
    assert event.address == "8 Boulevard du Port"
    assert Event.objects.count() == 1


def png(width, height):
    """A plain PNG of any size, written by hand: the suite has no imaging library."""

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    rows = (b"\x00" + b"\x40\x80\xc0" * width) * height
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


@pytest.fixture
def details_screen(funnel, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    choose_subcategory(funnel, "Salon")
    funnel.get_by_role("button", name="Continuer").click()
    return funnel


def import_image(page, name, mime_type, content):
    page.locator("input[type=file]").set_input_files(
        {"name": name, "mimeType": mime_type, "buffer": content}
    )


def test_an_imported_image_is_shrunk_to_a_webp_before_its_upload(details_screen):
    import_image(details_screen, "photo.png", "image/png", png(2400, 1600))

    expect(details_screen.get_by_role("button", name="Supprimer le visuel")).to_be_visible()
    assert details_screen.locator("input[name=image]").input_value().endswith(".webp")
    preview = details_screen.locator("[data-image-preview] img")
    assert preview.evaluate("img => [img.naturalWidth, img.naturalHeight]") == [1200, 800]


def test_an_image_already_small_keeps_its_size(details_screen):
    import_image(details_screen, "photo.png", "image/png", png(600, 400))

    expect(details_screen.get_by_role("button", name="Supprimer le visuel")).to_be_visible()
    preview = details_screen.locator("[data-image-preview] img")
    assert preview.evaluate("img => [img.naturalWidth, img.naturalHeight]") == [600, 400]


def test_a_browser_that_cannot_encode_webp_uploads_a_jpeg(details_screen):
    """Safari hands back a PNG when asked for a WebP, without a word."""
    details_screen.evaluate(
        """() => {
            const toBlob = HTMLCanvasElement.prototype.toBlob;
            HTMLCanvasElement.prototype.toBlob = function (callback, type, quality) {
                const encoded = type === "image/webp" ? "image/png" : type;
                return toBlob.call(this, callback, encoded, quality);
            };
        }"""
    )

    import_image(details_screen, "photo.png", "image/png", png(2400, 1600))

    expect(details_screen.get_by_role("button", name="Supprimer le visuel")).to_be_visible()
    assert details_screen.locator("input[name=image]").input_value().endswith(".jpg")


def test_an_image_heavier_than_30_mo_is_refused_before_any_upload(details_screen):
    import_image(details_screen, "huge.png", "image/png", b"\x00" * (30 * 1024 * 1024 + 1))

    expect(
        details_screen.get_by_text("Ce visuel dépasse la taille maximale de 30,0")
    ).to_be_visible()
    assert details_screen.locator("input[name=image]").input_value() == ""


def test_an_image_the_browser_cannot_read_is_refused(details_screen):
    import_image(details_screen, "broken.png", "image/png", b"not an image")

    expect(details_screen.get_by_text("Ce visuel n'a pas pu être lu")).to_be_visible()
    assert details_screen.locator("input[name=image]").input_value() == ""


@pytest.fixture
def sentry_captures(details_screen):
    """Stands in for the Sentry SDK, which only loads where a DSN is configured."""
    details_screen.evaluate(
        """() => {
            window.captured = [];
            window.Sentry = {
                captureException: (error, context) =>
                    window.captured.push({ error: String(error), step: context.tags.upload_step }),
            };
        }"""
    )
    return lambda: details_screen.evaluate("() => window.captured")


def test_an_upload_the_bucket_refuses_is_reported_to_sentry(details_screen, sentry_captures):
    details_screen.route("**/uploads-locaux/**", lambda route: route.fulfill(status=403))

    import_image(details_screen, "photo.png", "image/png", png(600, 400))

    expect(details_screen.get_by_text("L'import du visuel a échoué")).to_be_visible()
    assert sentry_captures() == [{"error": "Error: HTTP 403", "step": "bucket"}]


def test_an_upload_cut_off_by_the_network_is_reported_to_sentry(details_screen, sentry_captures):
    """A refusal without a CORS header looks the same to the page: the fetch itself throws."""
    details_screen.route("**/uploads-locaux/**", lambda route: route.abort())

    import_image(details_screen, "photo.png", "image/png", png(600, 400))

    expect(details_screen.get_by_text("L'import du visuel a échoué")).to_be_visible()
    [capture] = sentry_captures()
    assert capture["step"] == "bucket"
    assert capture["error"].startswith("TypeError")


def test_a_format_the_app_refuses_is_not_reported_to_sentry(details_screen, sentry_captures):
    details_screen.route(
        "**/evenements/importer-un-visuel/",
        lambda route: route.fulfill(status=400, json={"error": "Ce format n'est pas accepté."}),
    )

    import_image(details_screen, "photo.png", "image/png", png(600, 400))

    expect(details_screen.get_by_text("Ce format n'est pas accepté.")).to_be_visible()
    assert sentry_captures() == []
