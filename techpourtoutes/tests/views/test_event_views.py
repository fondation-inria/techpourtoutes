import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from techpourtoutes.models import Event

FUNNEL_URL = "/coalition/proposer-un-evenement/"

locmem = override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    NEW_EVENT_RECIPIENTS=["agir@techpourtoutes.io"],
)

SUBCATEGORY = {"subcategory": Event.Subcategory.SALON}

DETAILS = {
    "organizer": "Numeum",
    "title": "Salon des métiers du numérique",
    "description": "Une journée pour rencontrer des professionnelles.",
    "start_date": "2026-10-01",
    "start_time": "09:00",
    "end_date": "2026-10-02",
    "end_time": "18:00",
}

LOCATION = {
    "location_type": Event.LocationType.PHYSICAL,
    "address": "8 Boulevard du Port",
    "postal_code": "80000",
    "city": "Amiens",
    "cog_code": "80021",
    "longitude": "2.29009",
    "latitude": "49.897443",
    "ban_id": "80021_6590_00008",
    "access_type": Event.AccessType.OPEN,
    "price": "0",
}


# The client carries every answer collected so far in hidden inputs, so a step is always
# posted with the whole payload rather than by chaining requests.
def answers(**overrides):
    return SUBCATEGORY | DETAILS | LOCATION | overrides


@pytest.mark.django_db
def test_the_funnel_is_reserved_to_pros(client, beneficiary):
    client.force_login(beneficiary)

    response = client.get(FUNNEL_URL, follow=True)

    assert response.redirect_chain[-1][0] == reverse("account")
    assert any("réservée aux professionnelles" in str(m) for m in response.context["messages"])


@pytest.mark.django_db
def test_an_anonymous_visitor_is_sent_to_the_login_page(client):
    response = client.get(FUNNEL_URL)

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]


@pytest.mark.django_db
def test_the_first_screen_asks_for_the_subcategory(client, pro):
    client.force_login(pro)

    content = client.get(FUNNEL_URL).content.decode()

    assert 'name="action" value="subcategory"' in content
    assert "voulez-vous proposer" in content


@pytest.mark.django_db
def test_a_valid_category_leads_to_the_details_screen(client, pro):
    client.force_login(pro)

    content = client.post(FUNNEL_URL, {"action": "subcategory", **SUBCATEGORY}).content.decode()

    assert 'name="action" value="details"' in content
    assert "Nom de l&#x27;organisateur" in content


@pytest.mark.django_db
def test_a_missing_category_stays_on_the_first_screen(client, pro):
    client.force_login(pro)

    content = client.post(FUNNEL_URL, {"action": "subcategory"}).content.decode()

    assert 'name="action" value="subcategory"' in content


@pytest.mark.django_db
def test_a_valid_details_screen_leads_to_the_location_screen(client, pro):
    client.force_login(pro)

    content = client.post(
        FUNNEL_URL, {"action": "details", **SUBCATEGORY, **DETAILS}
    ).content.decode()

    assert 'name="action" value="location"' in content
    assert "Où se déroule" in content


@pytest.mark.django_db
def test_the_details_screen_carries_the_category_forward(client, pro):
    client.force_login(pro)

    content = client.post(FUNNEL_URL, {"action": "subcategory", **SUBCATEGORY}).content.decode()

    assert 'name="subcategory" value="salon"' in content


@pytest.mark.django_db
def test_going_back_re_renders_the_previous_screen_prefilled(client, pro):
    client.force_login(pro)

    content = client.post(
        FUNNEL_URL, {"action": "back", "to": "location", **SUBCATEGORY, **DETAILS}
    ).content.decode()

    assert 'name="action" value="details"' in content
    assert "Salon des métiers du numérique" in content
    # The step's own fields come back as visible inputs, never also as hidden carried ones.
    assert 'type="hidden" name="title"' not in content


@pytest.mark.django_db
def test_an_unknown_action_falls_back_to_the_first_screen(client, pro):
    """A forged `action` must not skip a step: it is treated as the first one."""
    client.force_login(pro)

    content = client.post(FUNNEL_URL, {"action": "n-importe-quoi", **answers()}).content.decode()

    assert 'name="action" value="details"' in content


@pytest.mark.django_db
def test_going_back_from_an_unknown_step_lands_on_the_first_screen(client, pro):
    client.force_login(pro)

    content = client.post(
        FUNNEL_URL, {"action": "back", "to": "n-importe-quoi", **SUBCATEGORY}
    ).content.decode()

    assert 'name="action" value="subcategory"' in content


@pytest.mark.django_db
@locmem
def test_publishing_creates_a_pending_event_and_sends_both_mails(client, pro):
    client.force_login(pro)

    content = client.post(FUNNEL_URL, {"action": "location", **answers()}).content.decode()

    event = Event.objects.get()
    assert event.created_by == pro
    assert event.status == Event.Status.PENDING
    assert event.title == "Salon des métiers du numérique"
    assert "en cours de validation" in content
    assert {tuple(msg.to) for msg in mail.outbox} == {
        (pro.email,),
        ("agir@techpourtoutes.io",),
    }


@pytest.mark.django_db
@locmem
def test_publishing_re_validates_every_earlier_step(client, pro):
    """A forged payload must not slip past: the last screen replays all three validators."""
    client.force_login(pro)

    content = client.post(
        FUNNEL_URL, {"action": "location", **answers(end_date="2026-09-01")}
    ).content.decode()

    assert not Event.objects.exists()
    assert not mail.outbox
    assert 'name="action" value="details"' in content


@pytest.mark.django_db
@locmem
def test_publishing_an_online_event_stores_no_address(client, pro):
    client.force_login(pro)

    client.post(
        FUNNEL_URL,
        {
            "action": "location",
            **answers(
                location_type=Event.LocationType.ONLINE, online_url="https://example.org/live"
            ),
        },
    )

    event = Event.objects.get()
    assert event.online_url == "https://example.org/live"
    assert event.address == ""
    assert event.latitude is None
