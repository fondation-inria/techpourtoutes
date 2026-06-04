import re
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.urls import reverse


def _email_input_is_disabled(html):
    return bool(re.search(r'id="id_email"[^>]*\bdisabled\b', html))


@pytest.mark.django_db
def test_mentor_landing_get(client):
    assert client.get(reverse("mentor_landing")).status_code == 200


@pytest.mark.django_db
def test_mentor_landing_post_valid_redirects(client, valid_pro_data, mock_create_mentor):
    response = client.post(reverse("mentor_landing"), data=valid_pro_data)
    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")


@pytest.mark.django_db
def test_mentor_landing_post_invalid_rerenders_with_errors(client, valid_pro_data):
    response = client.post(reverse("mentor_landing"), data={**valid_pro_data, "email": ""})
    assert response.status_code == 200
    assert "form" in response.context
    messages = list(response.context["messages"])
    assert len(messages) > 0


@pytest.mark.django_db
def test_mentor_landing_post_duplicate_email_shows_error(client, valid_pro_data):
    from techpourtoutes.forms import ProForm

    form = ProForm(data=valid_pro_data)
    assert form.is_valid()
    form.save()

    response = client.post(reverse("mentor_landing"), data=valid_pro_data)
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_coalition_welcome_get(client):
    assert client.get(reverse("coalition_welcome")).status_code == 200


@pytest.mark.django_db
def test_mentor_landing_post_shows_error_on_create_mentor_failure(client, valid_pro_data):
    failed = MagicMock(success=False, failure=True, errors=["erreur de synchronisation"])
    with patch(
        "techpourtoutes.views.coalition_views.CreateMentor",
        return_value=failed,
    ):
        response = client.post(reverse("mentor_landing"), data=valid_pro_data)

    assert response.status_code == 200
    assert "erreur" in response.content.decode().lower()


@pytest.mark.django_db
def test_internships_landing_get(client):
    assert client.get(reverse("internships_landing")).status_code == 200


@pytest.mark.django_db
def test_work_ambassador_landing_get(client):
    assert client.get(reverse("work_ambassador_landing")).status_code == 200


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_work_ambassador_landing_post_valid_redirects(client, valid_pro_data):
    response = client.post(reverse("work_ambassador_landing"), data=valid_pro_data)
    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_work_ambassador_landing_post_valid_persists_engagement(client, valid_pro_data):
    from techpourtoutes.models import Pro

    client.post(reverse("work_ambassador_landing"), data=valid_pro_data)

    pro = Pro.objects.get(email=valid_pro_data["email"])
    assert "work_ambassador" in pro.engagements


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    COALITION_WORK_AMBASSADOR_RECIPIENTS=["ambassador@example.com"],
)
def test_work_ambassador_landing_post_valid_sends_welcome_and_new_pro_emails(
    client, valid_pro_data
):
    from django.core import mail

    client.post(reverse("work_ambassador_landing"), data=valid_pro_data)

    assert len(mail.outbox) == 2
    recipients = {tuple(msg.to) for msg in mail.outbox}
    assert (valid_pro_data["email"],) in recipients
    assert ("ambassador@example.com",) in recipients


@pytest.mark.django_db
def test_work_ambassador_landing_post_invalid_rerenders_with_errors(client, valid_pro_data):
    response = client.post(
        reverse("work_ambassador_landing"), data={**valid_pro_data, "email": ""}
    )
    assert response.status_code == 200
    assert response.context["form"].errors
    messages = list(response.context["messages"])
    assert len(messages) > 0


def _training_ambassador_data(**overrides):
    return {
        "civility": "Madame",
        "first_name": "Manon",
        "last_name": "Desbordes",
        "email": "manon@example.com",
        "phone": "0612345678",
        "structure_id": "0750001A",
        "structure_name": "Université Paris-Saclay",
        "postal_code": "75011",
        "terms_accepted": True,
        **overrides,
    }


@pytest.mark.django_db
def test_training_ambassador_landing_get(client):
    assert client.get(reverse("training_ambassador_landing")).status_code == 200


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_training_ambassador_landing_post_valid_redirects(client):
    response = client.post(
        reverse("training_ambassador_landing"), data=_training_ambassador_data()
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_training_ambassador_landing_post_valid_persists_student_pro(client):
    from techpourtoutes.models import Pro

    client.post(reverse("training_ambassador_landing"), data=_training_ambassador_data())

    pro = Pro.objects.get(email="manon@example.com")
    assert "training_ambassador" in pro.engagements
    assert pro.professional_situation == "student"
    assert pro.job_title == "Étudiante"


@pytest.mark.django_db
def test_training_ambassador_landing_get_authenticated_pro_does_not_prefill_structure_name(
    client, pro
):
    client.force_login(pro)
    response = client.get(reverse("training_ambassador_landing"))
    assert response.status_code == 200
    assert not response.context["form"].initial.get("structure_name")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_training_ambassador_landing_post_authenticated_pro_updates_pro(client, pro):
    from techpourtoutes.models import Pro

    client.force_login(pro)
    client.post(
        reverse("training_ambassador_landing"),
        data=_training_ambassador_data(email=pro.email, first_name="Modifiée"),
    )

    assert Pro.objects.count() == 1
    pro.refresh_from_db()
    assert pro.first_name == "Modifiée"
    assert "training_ambassador" in pro.engagements


def _workshop_data(**overrides):
    return {
        "civility": "Madame",
        "first_name": "Manon",
        "last_name": "Desbordes",
        "email": "manon@example.com",
        "job_title": "Enseignante",
        "structure_id": "0750001A",
        "structure_name": "Lycée Voltaire",
        "postal_code": "75011",
        "remark": "",
        "ateliers": ["future_of_tech", "future_of_ia"],
        "terms_accepted": True,
        **overrides,
    }


@pytest.mark.django_db
def test_workshops_landing_get(client):
    assert client.get(reverse("workshops_landing")).status_code == 200


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_workshops_landing_post_valid_creates_pro_and_enqueues_task(client):
    from techpourtoutes.models import Pro

    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task") as mock_task:
        response = client.post(reverse("workshops_landing"), data=_workshop_data())

    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")

    pro = Pro.objects.get(email="manon@example.com")
    assert pro.structure_id == "0750001A"
    assert "workshops" in pro.engagements
    mock_task.delay.assert_called_once_with(str(pro.pk), ["future_of_tech", "future_of_ia"], "")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_workshops_landing_post_valid_sends_welcome_email(client):
    from django.core import mail

    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task"):
        client.post(reverse("workshops_landing"), data=_workshop_data())

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["manon@example.com"]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_workshops_landing_post_valid_persists_one_request_per_type(client):
    from techpourtoutes.models import Pro, WorkshopRequest

    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task"):
        client.post(reverse("workshops_landing"), data=_workshop_data(remark="Une note"))

    pro = Pro.objects.get(email="manon@example.com")
    requests = pro.workshop_requests.all()
    assert {r.type for r in requests} == {"future_of_tech", "future_of_ia"}
    assert all(r.remark == "Une note" for r in requests)
    assert WorkshopRequest.objects.count() == 2


@pytest.mark.django_db
def test_workshops_landing_post_invalid_rerenders_with_errors(client):
    response = client.post(reverse("workshops_landing"), data=_workshop_data(ateliers=[]))
    assert response.status_code == 200
    assert response.context["form"].errors
    messages = list(response.context["messages"])
    assert len(messages) > 0


@pytest.mark.django_db
def test_sponsor_landing_get(client):
    assert client.get(reverse("sponsor_landing")).status_code == 200


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_sponsor_landing_post_valid_redirects(client, valid_pro_data):
    response = client.post(reverse("sponsor_landing"), data=valid_pro_data)
    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")


@pytest.mark.django_db
def test_sponsor_landing_post_invalid_rerenders_with_errors(client, valid_pro_data):
    response = client.post(reverse("sponsor_landing"), data={**valid_pro_data, "email": ""})
    assert response.status_code == 200
    assert response.context["form"].errors
    messages = list(response.context["messages"])
    assert len(messages) > 0


# --- Authenticated pro: GET exposes pro in context ---


@pytest.mark.django_db
def test_mentor_landing_get_authenticated_pro_passes_pro_to_context(client, pro):
    client.force_login(pro)
    response = client.get(reverse("mentor_landing"))
    assert response.status_code == 200
    assert response.context["pro"] == pro


@pytest.mark.django_db
def test_work_ambassador_landing_get_authenticated_pro_passes_pro_to_context(client, pro):
    client.force_login(pro)
    response = client.get(reverse("work_ambassador_landing"))
    assert response.status_code == 200
    assert response.context["pro"] == pro


@pytest.mark.django_db
def test_workshops_landing_get_authenticated_pro_passes_pro_to_context(client, pro):
    client.force_login(pro)
    response = client.get(reverse("workshops_landing"))
    assert response.status_code == 200
    assert response.context["pro"] == pro


@pytest.mark.django_db
def test_sponsor_landing_get_authenticated_pro_passes_pro_to_context(client, pro):
    client.force_login(pro)
    response = client.get(reverse("sponsor_landing"))
    assert response.status_code == 200
    assert response.context["pro"] == pro


@pytest.mark.django_db
def test_mentor_landing_disables_email_for_authenticated_pro(client, pro):
    client.force_login(pro)
    html = client.get(reverse("mentor_landing")).content.decode()
    assert _email_input_is_disabled(html)


@pytest.mark.django_db
def test_mentor_landing_email_editable_for_anonymous(client):
    html = client.get(reverse("mentor_landing")).content.decode()
    assert not _email_input_is_disabled(html)


@pytest.mark.django_db
def test_workshops_landing_disables_email_for_authenticated_pro(client, pro):
    client.force_login(pro)
    html = client.get(reverse("workshops_landing")).content.decode()
    assert _email_input_is_disabled(html)


@pytest.mark.django_db
def test_workshops_landing_email_editable_for_anonymous(client):
    html = client.get(reverse("workshops_landing")).content.decode()
    assert not _email_input_is_disabled(html)


# --- Authenticated pro POST: updates existing pro, does not create a new one ---


def _pro_post_data(pro, **overrides):
    return {
        "civility": pro.civility,
        "first_name": pro.first_name,
        "last_name": pro.last_name,
        "email": pro.email,
        "phone": str(pro.phone),
        "postal_code": pro.postal_code,
        "professional_situation": pro.professional_situation,
        "job_title": pro.job_title,
        "structure_name": pro.structure_name,
        "terms_accepted": True,
        **overrides,
    }


@pytest.mark.django_db
def test_mentor_landing_post_authenticated_pro_updates_pro(client, pro, mock_create_mentor):
    from techpourtoutes.models import Pro

    client.force_login(pro)
    client.post(reverse("mentor_landing"), data=_pro_post_data(pro, first_name="Modifiée"))

    assert Pro.objects.count() == 1


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_work_ambassador_landing_post_authenticated_pro_updates_pro(client, pro):
    from techpourtoutes.models import Pro

    client.force_login(pro)
    client.post(
        reverse("work_ambassador_landing"), data=_pro_post_data(pro, first_name="Modifiée")
    )

    assert Pro.objects.count() == 1
    pro.refresh_from_db()
    assert pro.first_name == "Modifiée"
    assert "work_ambassador" in pro.engagements


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_workshops_landing_post_authenticated_pro_updates_pro(client, pro):
    from techpourtoutes.models import Pro

    client.force_login(pro)
    data = _workshop_data(email=pro.email, first_name="Modifiée")
    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task"):
        client.post(reverse("workshops_landing"), data=data)

    assert Pro.objects.count() == 1
    pro.refresh_from_db()
    assert pro.first_name == "Modifiée"
    assert "workshops" in pro.engagements


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_sponsor_landing_post_authenticated_pro_updates_pro(client, pro):
    from techpourtoutes.models import Pro

    client.force_login(pro)
    client.post(reverse("sponsor_landing"), data=_pro_post_data(pro, first_name="Modifiée"))

    assert Pro.objects.count() == 1
    pro.refresh_from_db()
    assert pro.first_name == "Modifiée"
    assert "sponsor" in pro.engagements
