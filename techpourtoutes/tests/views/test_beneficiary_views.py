from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

NEW_UPCOMING_FEATURE_NOTIFICATION_URL = "/bientot-disponible/"
CREATE_UPCOMING_FEATURE_NOTIFICATION_URL = "/bientot-disponible/inscription/"


@pytest.mark.django_db
def test_new_upcoming_feature_notification_get_returns_200(client):
    assert client.get(NEW_UPCOMING_FEATURE_NOTIFICATION_URL).status_code == 200


@pytest.mark.django_db
@override_settings(BREVO_SYNC_ENABLED=True)
def test_create_upcoming_feature_notification_valid_pushes_brevo_contact_and_redirects(client):
    with patch(
        "techpourtoutes.views.beneficiary_views.create_upcoming_feature_notification_task"
    ) as mock_task:
        response = client.post(
            CREATE_UPCOMING_FEATURE_NOTIFICATION_URL, data={"email": "hedy@example.com"}
        )

    assert response.status_code == 302
    assert response.url == NEW_UPCOMING_FEATURE_NOTIFICATION_URL
    mock_task.delay.assert_called_once_with(email="hedy@example.com")


@pytest.mark.django_db
@override_settings(BREVO_SYNC_ENABLED=False)
def test_create_upcoming_feature_notification_skips_task_when_sync_disabled(client):
    with patch(
        "techpourtoutes.views.beneficiary_views.create_upcoming_feature_notification_task"
    ) as mock_task:
        response = client.post(
            CREATE_UPCOMING_FEATURE_NOTIFICATION_URL, data={"email": "hedy@example.com"}
        )

    assert response.status_code == 302
    mock_task.delay.assert_not_called()


@pytest.mark.django_db
def test_create_upcoming_feature_notification_invalid_rerenders_with_errors(client):
    response = client.post(
        CREATE_UPCOMING_FEATURE_NOTIFICATION_URL, data={"email": "not-an-email"}
    )
    assert response.status_code == 200
    assert response.context["form"].errors
    messages = list(response.context["messages"])
    assert len(messages) > 0


NEW_MENTOREE_URL = "/trouver-une-mentore/"


@pytest.mark.django_db
def test_new_mentoree_cta_for_anonymous_user(client):
    response = client.get(NEW_MENTOREE_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == "/inscription/?wants_mentor=1"
    assert response.context["cta_label"] == "S'inscrire au mentorat"
    assert response.context["cta_disabled"] is False


@pytest.mark.django_db
def test_new_mentoree_cta_for_connected_unregistered_beneficiary(client, beneficiary):
    client.force_login(beneficiary)

    response = client.get(NEW_MENTOREE_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == "/devenir-mentoree/"
    assert response.context["cta_label"] == "S'inscrire au mentorat"
    assert response.context["cta_disabled"] is False


@pytest.mark.django_db
def test_new_mentoree_cta_for_connected_registered_beneficiary(client, beneficiary):
    beneficiary.jobirl_user_id = 42
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.get(NEW_MENTOREE_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == reverse("login_to_jobirl")
    assert response.context["cta_label"] == "Rejoindre mon espace mentorat"
    assert response.context["cta_disabled"] is False


@pytest.mark.django_db
def test_new_mentoree_cta_disabled_for_registration_pending_jobirl_account(client, beneficiary):
    beneficiary.legal_representative_email = "parent.durand@example.com"
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.get(NEW_MENTOREE_URL)

    assert response.status_code == 200
    assert response.context["cta_label"] == "Rejoindre mon espace mentorat"
    assert response.context["cta_disabled"] is True


@pytest.mark.django_db
def test_new_mentoree_cta_for_connected_non_beneficiary_points_to_mentoring_funnel(client, pro):
    client.force_login(pro)

    response = client.get(NEW_MENTOREE_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == "/devenir-mentoree/"
    assert response.context["cta_label"] == "S'inscrire au mentorat"
    assert response.context["cta_disabled"] is False


INDEX_EVENTS_URL = "/evenements/"


def approved_event(pro, **overrides):
    from techpourtoutes.models import Event

    from ..models.test_event import build_event

    return build_event(pro, **{"status": Event.Status.APPROVED, **overrides})


@pytest.fixture
def salon(pro):
    event = approved_event(pro, title="Salon des métiers du numérique")
    event.save()
    return event


@pytest.mark.django_db
def test_index_events_is_open_to_anonymous_visitors(client, salon):
    response = client.get(INDEX_EVENTS_URL)

    assert response.status_code == 200
    assert salon.title.encode() in response.content


@pytest.mark.django_db
def test_index_events_hides_events_awaiting_validation(client, event):
    """The `event` fixture is PENDING: only approved events reach the page."""
    response = client.get(INDEX_EVENTS_URL)

    assert event.title.encode() not in response.content


@pytest.mark.django_db
def test_index_events_hides_rejected_events(client, pro):
    from techpourtoutes.models import Event

    approved_event(pro, title="Forum annulé", status=Event.Status.REJECTED).save()

    assert b"Forum annul" not in client.get(INDEX_EVENTS_URL).content


@pytest.mark.django_db
def test_index_events_hides_past_events(client, pro):
    today = timezone.localdate()
    approved_event(
        pro,
        title="Hackathon de l'an dernier",
        start_date=today - timedelta(days=3),
        end_date=today - timedelta(days=1),
    ).save()

    assert b"an dernier" not in client.get(INDEX_EVENTS_URL).content


@pytest.mark.django_db
def test_index_events_lists_from_the_nearest_to_the_furthest(client, pro):
    today = timezone.localdate()
    for title, days in [("Dans deux mois", 60), ("Dans cinq jours", 5), ("Dans un mois", 30)]:
        approved_event(
            pro,
            title=title,
            start_date=today + timedelta(days=days),
            end_date=today + timedelta(days=days),
        ).save()

    content = client.get(INDEX_EVENTS_URL).content

    assert (
        content.index(b"Dans cinq jours")
        < content.index(b"Dans un mois")
        < content.index(b"Dans deux mois")
    )


@pytest.mark.django_db
def test_index_events_cards_link_to_the_event_detail_page(client, salon):
    content = client.get(INDEX_EVENTS_URL).content

    assert reverse("show_event", args=[salon.pk]).encode() in content


@pytest.mark.django_db
def test_index_events_marks_the_events_a_beneficiary_already_saved(client, beneficiary, salon):
    from techpourtoutes.models import SavedEvent

    SavedEvent.objects.toggle(event=salon, beneficiary=beneficiary)
    client.force_login(beneficiary)

    response = client.get(INDEX_EVENTS_URL)

    assert response.context["events"][0].saved is True
    assert b'aria-pressed="true"' in response.content


@pytest.mark.django_db
def test_index_events_leaves_an_unsaved_event_unmarked(client, beneficiary, salon):
    client.force_login(beneficiary)

    response = client.get(INDEX_EVENTS_URL)

    assert response.context["events"][0].saved is False
    assert b'aria-pressed="false"' in response.content


@pytest.mark.django_db
def test_index_events_saved_flag_costs_no_query_per_event(client, beneficiary, pro):
    """Four events must cost what one costs: the flag is annotated, never fetched per row."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    approved_event(pro, title="Événement 0").save()
    client.force_login(beneficiary)
    with CaptureQueriesContext(connection) as one_event:
        client.get(INDEX_EVENTS_URL)

    for index in range(1, 4):
        approved_event(pro, title=f"Événement {index}").save()
    with CaptureQueriesContext(connection) as four_events:
        client.get(INDEX_EVENTS_URL)

    assert len(four_events.captured_queries) == len(one_event.captured_queries)


@pytest.mark.django_db
def test_index_events_bookmark_posts_to_update_saved_event(client, beneficiary, salon):
    client.force_login(beneficiary)

    content = client.get(INDEX_EVENTS_URL).content

    assert reverse("update_saved_event", args=[salon.pk]).encode() in content


@pytest.mark.django_db
def test_index_events_anonymous_bookmark_opens_the_signup_modal(client, salon):
    content = client.get(INDEX_EVENTS_URL).content

    assert reverse("create_saved_event_modal").encode() in content


@pytest.mark.django_db
def test_index_events_gives_a_connected_pro_no_bookmark_at_all(client, pro, salon):
    client.force_login(pro)

    content = client.get(INDEX_EVENTS_URL).content

    assert reverse("create_saved_event_modal").encode() not in content
    assert b"#bookmark" not in content


@pytest.mark.django_db
def test_index_events_shows_fifteen_events_and_a_link_to_the_next_page(client, pro):
    for index in range(16):
        approved_event(pro, title=f"Événement {index:02d}").save()

    response = client.get(INDEX_EVENTS_URL)

    assert len(response.context["events"].object_list) == 15
    assert b'href="?page=2"' in response.content


@pytest.mark.django_db
def test_index_events_serves_the_page_asked_for(client, pro):
    for index in range(16):
        approved_event(pro, title=f"Événement {index:02d}").save()

    response = client.get(INDEX_EVENTS_URL, {"page": 2})

    assert response.status_code == 200
    assert response.context["events"].number == 2
    assert len(response.context["events"].object_list) == 1
    assert b'aria-current="page"' in response.content


@pytest.mark.django_db
def test_index_events_hides_the_pagination_when_one_page_is_enough(client, salon):
    assert b"join-item" not in client.get(INDEX_EVENTS_URL).content


@pytest.mark.django_db
def test_index_events_falls_back_to_the_first_page_on_a_bogus_number(client, salon):
    response = client.get(INDEX_EVENTS_URL, {"page": "banane"})

    assert response.status_code == 200
    assert response.context["events"].number == 1


@pytest.mark.django_db
def test_update_saved_event_saves_the_event_for_the_beneficiary(client, beneficiary, salon):
    from techpourtoutes.models import SavedEvent

    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_event", args=[salon.pk]))

    assert response.status_code == 200
    assert SavedEvent.objects.count() == 1
    assert b'aria-pressed="true"' in response.content
    assert b"text-blue-500" in response.content


@pytest.mark.django_db
def test_update_saved_event_twice_takes_the_event_back_out(client, beneficiary, salon):
    from techpourtoutes.models import SavedEvent

    client.force_login(beneficiary)
    url = reverse("update_saved_event", args=[salon.pk])
    client.post(url)

    response = client.post(url)

    assert SavedEvent.objects.count() == 0
    assert b'aria-pressed="false"' in response.content


@pytest.mark.django_db
def test_update_saved_event_twice_leaves_the_bookmark_transparent(client, beneficiary, salon):
    client.force_login(beneficiary)
    url = reverse("update_saved_event", args=[salon.pk])
    client.post(url)

    response = client.post(url)

    assert b"text-blue-500" not in response.content


@pytest.mark.django_db
def test_update_saved_event_rejects_a_get(client, beneficiary, salon):
    client.force_login(beneficiary)

    response = client.get(reverse("update_saved_event", args=[salon.pk]))

    assert response.status_code == 405


@pytest.mark.django_db
def test_update_saved_event_requires_a_login(client, salon):
    response = client.post(reverse("update_saved_event", args=[salon.pk]))

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]


@pytest.mark.django_db
def test_update_saved_event_is_closed_to_pros(client, pro, salon):
    from techpourtoutes.models import SavedEvent

    client.force_login(pro)

    response = client.post(reverse("update_saved_event", args=[salon.pk]))

    assert response.status_code == 404
    assert SavedEvent.objects.count() == 0


@pytest.mark.django_db
def test_update_saved_event_ignores_an_event_awaiting_validation(client, beneficiary, event):
    from techpourtoutes.models import SavedEvent

    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_event", args=[event.pk]))

    assert response.status_code == 404
    assert SavedEvent.objects.count() == 0


@pytest.mark.django_db
def test_create_saved_event_modal_offers_signing_up_and_logging_in(client):
    response = client.get(reverse("create_saved_event_modal"))

    assert response.status_code == 200
    assert b"Rejoins le club TechPourToutes" in response.content
    assert reverse("inscription_funnel").encode() in response.content
    assert reverse("login_request").encode() in response.content
