from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse


@pytest.mark.django_db
def test_new_mentor_get(client):
    assert client.get(reverse("new_mentor")).status_code == 200


@pytest.mark.django_db
def test_new_internship_get(client):
    response = client.get(reverse("new_internship"))

    assert response.status_code == 200
    assert response.templates[0].name == "coalition/new_internship.html"


@pytest.mark.django_db
def test_new_work_ambassador_get(client):
    assert client.get(reverse("new_work_ambassador")).status_code == 200


@pytest.mark.django_db
def test_new_training_ambassador_get(client):
    assert client.get(reverse("new_training_ambassador")).status_code == 200


@pytest.mark.django_db
def test_new_workshop_request_get(client):
    assert client.get(reverse("new_workshop_request")).status_code == 200


@pytest.mark.django_db
def test_new_structure_engagement_get(client):
    assert client.get(reverse("new_structure_engagement")).status_code == 200


@pytest.mark.django_db
def test_sponsor_page_redirects_permanently_to_new_structure_engagement(client):
    response = client.get("/coalition/devenir-mecene/")

    assert response.status_code == 301
    assert response["Location"] == reverse("new_structure_engagement")


@pytest.mark.django_db
@pytest.mark.parametrize("page", ["new_internship", "new_structure_engagement"])
def test_pages_send_anonymous_visitor_to_inscription_funnel_before_events(client, page):
    html = client.get(reverse(page)).content.decode()

    assert f'href="{reverse("new_pro_inscription_funnel")}?engagement=events"' in html
    assert f'href="{reverse("new_event")}"' not in html


@pytest.mark.django_db
@pytest.mark.parametrize("page", ["new_internship", "new_structure_engagement"])
def test_pages_send_signed_in_pro_to_new_event(client, pro, page):
    client.force_login(pro)

    html = client.get(reverse(page)).content.decode()

    assert f'href="{reverse("new_event")}"' in html
    assert f"?next={reverse('index_pro_events')}" not in html


_ENGAGEMENT_PAGES = [
    ("new_mentor", "mentor"),
    ("new_work_ambassador", "work_ambassador"),
    ("new_training_ambassador", "training_ambassador"),
    ("new_workshop_request", "workshops"),
    ("new_structure_engagement", "sponsor"),
    ("new_structure_engagement", "mobilize_structure"),
]


@pytest.mark.django_db
@pytest.mark.parametrize(("page", "engagement"), _ENGAGEMENT_PAGES)
def test_engagement_pages_send_anonymous_visitor_to_inscription_funnel(client, page, engagement):
    html = client.get(reverse(page)).content.decode()
    engagement_url = reverse("new_pro_engagement", args=[engagement])
    assert f'href="{engagement_url}"' in html

    response = client.get(engagement_url)

    assert response["Location"] == (
        f"{reverse('new_pro_inscription_funnel')}?engagement={engagement}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(("page", "engagement"), _ENGAGEMENT_PAGES)
def test_engagement_pages_link_pro_with_a_screen_left_to_new_pro_engagement(
    client, pro, page, engagement
):
    client.force_login(pro)

    html = client.get(reverse(page)).content.decode()

    assert f'href="{reverse("new_pro_engagement", args=[engagement])}"' in html


@pytest.mark.django_db
def test_new_mentor_lets_pro_with_nothing_left_to_give_add_the_engagement_at_once(client, pro):
    pro.structure_type = "company"
    pro.save()
    client.force_login(pro)

    html = client.get(reverse("new_mentor")).content.decode()

    add_url = reverse("create_pro_engagement", args=["mentor"])
    assert f'hx-post="{add_url}?next={reverse("new_mentor")}"' in html
    assert f'href="{reverse("new_pro_engagement", args=["mentor"])}"' not in html


@pytest.mark.django_db
@pytest.mark.parametrize(("page", "engagement"), _ENGAGEMENT_PAGES)
def test_engagement_pages_show_beneficiary_no_engagement_button(
    client, beneficiary, page, engagement
):
    client.force_login(beneficiary)

    html = client.get(reverse(page)).content.decode()

    assert reverse("new_pro_engagement", args=[engagement]) not in html
    assert reverse("create_pro_engagement", args=[engagement]) not in html


@pytest.mark.django_db
@pytest.mark.parametrize("page", ["coalition_home", "html_sitemap"])
def test_pages_link_new_structure_engagement(client, page):
    html = client.get(reverse(page)).content.decode()

    assert f'href="{reverse("new_structure_engagement")}"' in html


def _signature_data(**overrides):
    return {
        "first_name": "Manon",
        "last_name": "Desbordes",
        "email": "manon@example.com",
        "structure_name": "Latitudes",
        **overrides,
    }


@pytest.mark.django_db
def test_new_manifeste_signature_get(client):
    assert client.get(reverse("new_manifeste_signature")).status_code == 200


@pytest.mark.django_db
@override_settings(BREVO_SYNC_ENABLED=True)
def test_create_manifeste_signature_valid_pushes_brevo_contact_and_redirects(client):
    from techpourtoutes.models import User

    with patch(
        "techpourtoutes.views.coalition_views.upsert_manifeste_signatory_task"
    ) as mock_task:
        response = client.post(reverse("create_manifeste_signature"), data=_signature_data())

    assert response.status_code == 302
    assert response["Location"] == reverse("show_manifeste_signature")
    mock_task.delay.assert_called_once_with(
        first_name="Manon",
        last_name="Desbordes",
        email="manon@example.com",
        structure_name="Latitudes",
    )
    assert not User.objects.filter(email="manon@example.com").exists()


@pytest.mark.django_db
@override_settings(BREVO_SYNC_ENABLED=False)
def test_create_manifeste_signature_skips_task_when_sync_disabled(client):
    with patch(
        "techpourtoutes.views.coalition_views.upsert_manifeste_signatory_task"
    ) as mock_task:
        response = client.post(reverse("create_manifeste_signature"), data=_signature_data())

    assert response.status_code == 302
    mock_task.delay.assert_not_called()


@pytest.mark.django_db
def test_create_manifeste_signature_invalid_rerenders_with_errors(client):
    response = client.post(
        reverse("create_manifeste_signature"), data=_signature_data(email="not-an-email")
    )
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
@override_settings(SITE_URL="https://example.test")
def test_show_manifeste_signature_linkedin_share_url(client):
    response = client.get(reverse("show_manifeste_signature"))
    assert response.context["linkedin_share_url"] == (
        "https://www.linkedin.com/sharing/share-offsite/?url=https://example.test/notre-manifeste/"
    )


@pytest.mark.django_db
def test_show_manifeste_signature_returns_200(client):
    assert client.get(reverse("show_manifeste_signature")).status_code == 200
