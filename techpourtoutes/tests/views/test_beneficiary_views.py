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


def other_pro(valid_pro_model_data):
    """A pro who is not the author of the fixture events."""
    from techpourtoutes.models import Pro

    pro = Pro(**{**valid_pro_model_data, "username": "bea@example.com"})
    pro.save()
    return pro


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

    assert reverse("show_event", args=[salon.slug]).encode() in content


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

    assert reverse("create_saved_event_modal", args=[salon.pk]).encode() in content


@pytest.mark.django_db
def test_index_events_gives_a_connected_pro_no_bookmark_at_all(client, pro, salon):
    client.force_login(pro)

    content = client.get(INDEX_EVENTS_URL).content

    assert reverse("create_saved_event_modal", args=[salon.pk]).encode() not in content
    assert b"#bookmark" not in content


@pytest.mark.django_db
def test_index_events_shows_eighteen_events_and_a_link_to_the_next_page(client, pro):
    for index in range(20):
        approved_event(pro, title=f"Événement {index:02d}").save()

    response = client.get(INDEX_EVENTS_URL)

    assert len(response.context["events"].object_list) == 18
    assert b'href="?page=2"' in response.content


@pytest.mark.django_db
def test_index_events_serves_the_page_asked_for(client, pro):
    for index in range(20):
        approved_event(pro, title=f"Événement {index:02d}").save()

    response = client.get(INDEX_EVENTS_URL, {"page": 2})

    assert response.status_code == 200
    assert response.context["events"].number == 2
    assert len(response.context["events"].object_list) == 2
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
def test_create_saved_event_modal_offers_signing_up_and_logging_in(client, salon):
    response = client.get(reverse("create_saved_event_modal", args=[salon.pk]))

    assert response.status_code == 200
    assert b"Rejoins le club TechPourToutes" in response.content
    assert reverse("inscription_funnel").encode() in response.content
    assert reverse("login_request").encode() in response.content


@pytest.mark.django_db
def test_create_saved_event_modal_carries_the_event_into_both_ways_in(client, salon):
    content = client.get(reverse("create_saved_event_modal", args=[salon.pk])).content.decode()

    assert f"{reverse('inscription_funnel')}?saved_event={salon.pk}" in content
    assert f"{reverse('login_request')}?saved_event={salon.pk}" in content


@pytest.mark.django_db
def test_create_saved_event_modal_ignores_an_event_awaiting_validation(client, event):
    assert client.get(reverse("create_saved_event_modal", args=[event.pk])).status_code == 404


@pytest.mark.django_db
def test_show_event_renders_the_event(client, salon):
    response = client.get(reverse("show_event", args=[salon.slug]))

    assert response.status_code == 200
    assert salon.title.encode() in response.content


@pytest.mark.django_db
def test_show_event_makes_the_links_in_the_description_clickable(client, pro):
    event = approved_event(
        pro,
        title="Salon avec un lien",
        description="Programme sur https://techpourtoutes.io\n<b>pas du gras</b>",
    )
    event.save()

    content = client.get(reverse("show_event", args=[event.slug])).content.decode()

    anchor = content[content.index('<a href="https://techpourtoutes.io"') :].split("</a>")[0]
    assert 'target="_blank"' in anchor
    assert 'rel="nofollow noopener noreferrer"' in anchor
    assert "underline" in anchor
    # The description goes through `linebreaksbr`: the icon has to come out of it in one piece.
    assert "#external-link" in anchor
    assert "<br>" not in anchor
    # What surrounds the link is still escaped, and the line break still becomes a <br>.
    assert "<b>pas du gras</b>" not in content
    assert "&lt;b&gt;pas du gras&lt;/b&gt;" in content
    assert "<br>" in content


@pytest.mark.django_db
def test_show_event_shows_the_minutes_of_the_opening_hours(client, pro):
    from datetime import time

    event = approved_event(pro, start_time=time(9, 30), end_time=time(17, 45))
    event.save()

    content = client.get(reverse("show_event", args=[event.slug])).content.decode()

    assert "entre 9h30 et 17h45" in content


@pytest.mark.django_db
def test_show_event_hides_events_awaiting_validation(client, event):
    response = client.get(reverse("show_event", args=[event.slug]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_show_event_shows_the_city_tag_and_address_for_a_physical_event(client, pro):
    from techpourtoutes.models import Event

    physical = approved_event(
        pro,
        location_type=Event.LocationType.PHYSICAL,
        address="8 Boulevard du Port",
        postal_code="80000",
        city="Amiens",
        longitude=2.29009,
        latitude=49.897443,
    )
    physical.save()

    content = client.get(reverse("show_event", args=[physical.slug])).content.decode()

    assert "Amiens" in content
    assert "Adresse" in content
    assert "8 Boulevard du Port" in content


@pytest.mark.django_db
def test_show_event_hides_the_city_tag_and_shows_online_for_an_online_event(client, pro):
    from techpourtoutes.models import Event

    online = approved_event(
        pro,
        location_type=Event.LocationType.ONLINE,
        city="",
        online_url="https://meet.example.com/abc",
    )
    online.save()

    content = client.get(reverse("show_event", args=[online.slug])).content.decode()

    assert "En ligne" in content
    assert "Adresse" not in content
    assert "https://meet.example.com/abc" in content


@pytest.mark.django_db
def test_show_event_shows_no_cta_for_an_open_event(client, pro):
    from techpourtoutes.models import Event

    open_event = approved_event(pro, access_type=Event.AccessType.OPEN)
    open_event.save()

    content = client.get(reverse("show_event", args=[open_event.slug])).content

    assert reverse("show_participation_modal", args=[open_event.pk]).encode() not in content


@pytest.mark.django_db
def test_show_event_shows_a_participate_cta_for_a_registration_event(client, pro):
    from techpourtoutes.models import Event

    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()

    response = client.get(reverse("show_event", args=[registration.slug]))

    assert "Participer" in response.content.decode()
    assert reverse("show_participation_modal", args=[registration.pk]).encode() in response.content


@pytest.mark.django_db
def test_show_event_shows_a_candidacy_cta_for_a_candidacy_event(client, pro):
    from techpourtoutes.models import Event

    candidacy = approved_event(pro, access_type=Event.AccessType.CANDIDACY)
    candidacy.save()

    response = client.get(reverse("show_event", args=[candidacy.slug]))

    assert "Candidater" in response.content.decode()
    assert reverse("show_participation_modal", args=[candidacy.pk]).encode() in response.content


@pytest.mark.django_db
def test_show_event_shows_the_participation_cta_to_a_connected_pro(
    client, pro, valid_pro_model_data
):
    from techpourtoutes.models import Event

    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()
    client.force_login(other_pro(valid_pro_model_data))

    content = client.get(reverse("show_event", args=[registration.slug])).content

    assert reverse("show_participation_modal", args=[registration.pk]).encode() in content


@pytest.mark.django_db
def test_show_event_lets_the_author_open_her_event_awaiting_validation(client, pro, event):
    client.force_login(pro)

    response = client.get(reverse("show_event", args=[event.slug]))

    assert response.status_code == 200
    assert event.title in response.content.decode()


@pytest.mark.django_db
def test_show_event_hides_an_event_awaiting_validation_from_another_pro(
    client, event, valid_pro_model_data
):
    client.force_login(other_pro(valid_pro_model_data))

    assert client.get(reverse("show_event", args=[event.slug])).status_code == 404


@pytest.mark.django_db
def test_show_event_hides_an_event_awaiting_validation_from_a_beneficiary(
    client, beneficiary, event
):
    client.force_login(beneficiary)

    assert client.get(reverse("show_event", args=[event.slug])).status_code == 404


@pytest.mark.django_db
def test_show_event_lets_a_staff_member_open_an_event_awaiting_validation(client, event):
    from techpourtoutes.models import User

    staff = User.objects.create_user(
        username="staff@example.com",
        email="staff@example.com",
        first_name="Ada",
        last_name="Moderatrice",
        is_staff=True,
    )
    client.force_login(staff)

    assert client.get(reverse("show_event", args=[event.slug])).status_code == 200


@pytest.mark.django_db
def test_show_event_offers_the_author_a_link_to_edit_instead_of_participating(client, pro):
    from techpourtoutes.models import Event

    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()
    client.force_login(pro)

    content = client.get(reverse("show_event", args=[registration.slug])).content.decode()

    assert "Modifier" in content
    assert reverse("edit_event", args=[registration.pk]) in content
    assert reverse("show_participation_modal", args=[registration.pk]) not in content


@pytest.mark.django_db
def test_show_event_offers_the_author_a_link_to_edit_an_event_open_to_all(client, pro):
    """The edit CTA does not hang off the registration link: an open event carries it too."""
    from techpourtoutes.models import Event

    open_event = approved_event(pro, access_type=Event.AccessType.OPEN)
    open_event.save()
    client.force_login(pro)

    content = client.get(reverse("show_event", args=[open_event.slug])).content.decode()

    assert reverse("edit_event", args=[open_event.pk]) in content


@pytest.mark.django_db
def test_show_event_hides_every_cta_once_the_event_has_ended(client, beneficiary, pro):
    from datetime import time

    from techpourtoutes.models import Event

    client.force_login(beneficiary)
    yesterday = timezone.localdate() - timedelta(days=1)
    past = approved_event(
        pro,
        access_type=Event.AccessType.REGISTRATION,
        start_date=yesterday,
        end_date=yesterday,
        end_time=time(18, 0),
    )
    past.save()

    response = client.get(reverse("show_event", args=[past.slug]))

    assert reverse("show_participation_modal", args=[past.pk]).encode() not in response.content
    assert reverse("update_saved_event", args=[past.pk]).encode() not in response.content


@pytest.mark.django_db
def test_show_event_gives_a_connected_pro_no_bookmark_at_all(client, pro, salon):
    client.force_login(pro)

    content = client.get(reverse("show_event", args=[salon.slug])).content

    assert reverse("create_saved_event_modal", args=[salon.pk]).encode() not in content
    assert reverse("update_saved_event", args=[salon.pk]).encode() not in content


@pytest.mark.django_db
def test_show_event_anonymous_bookmark_opens_the_signup_modal(client, salon):
    content = client.get(reverse("show_event", args=[salon.slug])).content

    assert reverse("create_saved_event_modal", args=[salon.pk]).encode() in content


@pytest.mark.django_db
def test_show_event_marks_an_already_saved_event(client, beneficiary, salon):
    from techpourtoutes.models import SavedEvent

    SavedEvent.objects.toggle(event=salon, beneficiary=beneficiary)
    client.force_login(beneficiary)

    content = client.get(reverse("show_event", args=[salon.slug])).content

    assert b'aria-pressed="true"' in content


@pytest.mark.django_db
def test_update_saved_event_with_label_shows_a_labeled_button(client, beneficiary, salon):
    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_event", args=[salon.pk]), {"label": "true"})

    assert "Retirer de mes événements" in response.content.decode()


@pytest.mark.django_db
def test_update_saved_event_with_label_shows_the_saved_confirmation(client, beneficiary, salon):
    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_event", args=[salon.pk]), {"label": "true"})

    assert "Événement enregistré" in response.content.decode()


@pytest.mark.django_db
def test_update_saved_event_without_label_hides_the_labeled_button(client, beneficiary, salon):
    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_event", args=[salon.pk]))

    assert "Retirer de mes événements" not in response.content.decode()


@pytest.mark.django_db
def test_update_saved_event_removing_a_labeled_bookmark_shows_the_removed_confirmation(
    client, beneficiary, salon
):
    client.force_login(beneficiary)
    url = reverse("update_saved_event", args=[salon.pk])
    client.post(url, {"label": "true"})

    response = client.post(url, {"label": "true"})

    content = response.content.decode()
    assert "Événement retiré" in content
    assert "Événement enregistré" not in content
    assert "Ajouter à mes événements" in content


@pytest.mark.django_db
def test_show_participation_modal_offers_the_external_link_for_registration(client, pro):
    from techpourtoutes.models import Event

    registration = approved_event(
        pro,
        access_type=Event.AccessType.REGISTRATION,
        registration_url="https://example.com/inscription",
    )
    registration.save()

    response = client.get(reverse("show_participation_modal", args=[registration.pk]))

    assert response.status_code == 200
    assert "pour t'inscrire" in response.content.decode()
    assert b"https://example.com/inscription" in response.content


@pytest.mark.django_db
def test_show_participation_modal_offers_the_external_link_for_candidacy(client, pro):
    from techpourtoutes.models import Event

    candidacy = approved_event(
        pro,
        access_type=Event.AccessType.CANDIDACY,
        registration_url="https://example.com/candidature",
    )
    candidacy.save()

    response = client.get(reverse("show_participation_modal", args=[candidacy.pk]))

    assert "pour candidater" in response.content.decode()
    assert b"https://example.com/candidature" in response.content


@pytest.mark.django_db
def test_show_participation_modal_offers_saving_the_event_to_a_connected_beneficiary(
    client, beneficiary, pro
):
    from techpourtoutes.models import Event

    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()
    client.force_login(beneficiary)

    response = client.get(reverse("show_participation_modal", args=[registration.pk]))

    assert reverse("update_saved_event", args=[registration.pk]).encode() in response.content


@pytest.mark.django_db
def test_show_participation_modal_hides_saving_from_an_anonymous_visitor(client, pro):
    from techpourtoutes.models import Event

    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()

    response = client.get(reverse("show_participation_modal", args=[registration.pk]))

    assert reverse("update_saved_event", args=[registration.pk]).encode() not in response.content


@pytest.mark.django_db
def test_show_participation_modal_hides_saving_from_a_connected_pro(client, pro):
    from techpourtoutes.models import Event

    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()
    client.force_login(pro)

    response = client.get(reverse("show_participation_modal", args=[registration.pk]))

    assert reverse("update_saved_event", args=[registration.pk]).encode() not in response.content


@pytest.mark.django_db
def test_show_participation_modal_ignores_an_event_awaiting_validation(client, event):
    response = client.get(reverse("show_participation_modal", args=[event.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_show_event_back_link_keeps_the_listing_page_and_filters(client, salon):
    response = client.get(
        reverse("show_event", args=[salon.slug]),
        HTTP_REFERER=f"http://testserver{INDEX_EVENTS_URL}?page=3&q=hackathon",
    )

    assert response.context["back_url"] == f"{INDEX_EVENTS_URL}?page=3&q=hackathon"


@pytest.mark.django_db
def test_show_event_back_link_falls_back_to_the_bare_listing(client, salon):
    response = client.get(reverse("show_event", args=[salon.slug]))

    assert response.context["back_url"] == INDEX_EVENTS_URL


@pytest.mark.django_db
def test_show_event_back_link_keeps_the_pro_events_page(client, salon):
    response = client.get(
        reverse("show_event", args=[salon.slug]),
        HTTP_REFERER=f"http://testserver{reverse('index_pro_events')}",
    )

    assert response.context["back_url"] == reverse("index_pro_events")


@pytest.mark.django_db
def test_show_event_back_link_trusts_a_back_param_from_the_pro_events_page(client, salon):
    """The edit-event funnel redirects here with `?back=...` rather than a matching referer,
    since the previous page in the browser's history is the funnel itself."""
    response = client.get(
        reverse("show_event", args=[salon.slug]), {"back": reverse("index_pro_events")}
    )

    assert response.context["back_url"] == reverse("index_pro_events")


@pytest.mark.django_db
def test_show_event_back_link_ignores_an_unsafe_back_param(client, salon):
    response = client.get(
        reverse("show_event", args=[salon.slug]),
        {"back": "https://evil.example.com/mes-evenements/"},
    )

    assert response.context["back_url"] == INDEX_EVENTS_URL


@pytest.mark.django_db
def test_show_event_back_link_ignores_a_referer_from_anywhere_else(client, salon):
    response = client.get(
        reverse("show_event", args=[salon.slug]),
        HTTP_REFERER="https://evil.example.com/evenements/?page=3",
    )

    assert response.context["back_url"] == INDEX_EVENTS_URL


@pytest.mark.django_db
def test_update_saved_event_swaps_every_bookmark_of_the_event(client, beneficiary, salon):
    """The detail page shows the bookmark twice and the modal a third time: one toggle from
    any of them has to leave the others in the same state."""
    client.force_login(beneficiary)

    content = client.post(reverse("update_saved_event", args=[salon.pk])).content.decode()

    assert f"hx-swap-oob='outerHTML:[data-bookmark=\"{salon.pk}\"]'" in content
