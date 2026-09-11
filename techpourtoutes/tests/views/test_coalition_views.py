import re
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.urls import reverse


def _email_input_is_disabled(html):
    return bool(re.search(r'id="id_email"[^>]*\bdisabled\b', html))


@pytest.mark.django_db
def test_new_mentor_get(client):
    assert client.get(reverse("new_mentor")).status_code == 200


@pytest.mark.django_db
def test_create_mentor_valid_redirects(client, valid_pro_data, mock_create_mentor):
    response = client.post(reverse("create_mentor"), data=valid_pro_data)
    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")


@pytest.mark.django_db
def test_create_mentor_invalid_rerenders_with_errors(client, valid_pro_data):
    response = client.post(reverse("create_mentor"), data={**valid_pro_data, "email": ""})
    assert response.status_code == 200
    assert "form" in response.context
    messages = list(response.context["messages"])
    assert len(messages) > 0


@pytest.mark.django_db
def test_create_mentor_duplicate_email_shows_error(client, valid_pro_data):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(data=valid_pro_data)
    assert form.is_valid()
    form.save()

    response = client.post(reverse("create_mentor"), data=valid_pro_data)
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_coalition_welcome_get(client):
    assert client.get(reverse("coalition_welcome")).status_code == 200


@pytest.mark.django_db
def test_create_mentor_shows_error_on_create_mentor_failure(client, valid_pro_data):
    failed = MagicMock(success=False, failure=True, errors=["erreur de synchronisation"])
    with patch(
        "techpourtoutes.views.coalition_views.CreateMentor",
        return_value=failed,
    ):
        response = client.post(reverse("create_mentor"), data=valid_pro_data)

    assert response.status_code == 200
    assert "erreur" in response.content.decode().lower()


@pytest.mark.django_db
def test_new_internship_get(client):
    assert client.get(reverse("new_internship")).status_code == 200


@pytest.mark.django_db
def test_new_work_ambassador_get(client):
    assert client.get(reverse("new_work_ambassador")).status_code == 200


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_work_ambassador_valid_redirects(client, valid_pro_data):
    response = client.post(reverse("create_work_ambassador"), data=valid_pro_data)
    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_work_ambassador_valid_persists_engagement(client, valid_pro_data):
    from techpourtoutes.models import Pro

    client.post(reverse("create_work_ambassador"), data=valid_pro_data)

    pro = Pro.objects.get(email=valid_pro_data["email"])
    assert "work_ambassador" in pro.engagements


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    COALITION_WORK_AMBASSADOR_RECIPIENTS=["ambassador@example.com"],
)
def test_create_work_ambassador_sends_welcome_and_pro_signed_up_emails(client, valid_pro_data):
    from django.core import mail

    client.post(reverse("create_work_ambassador"), data=valid_pro_data)

    assert len(mail.outbox) == 2
    recipients = {tuple(msg.to) for msg in mail.outbox}
    assert (valid_pro_data["email"],) in recipients
    assert ("ambassador@example.com",) in recipients


@pytest.mark.django_db
def test_create_work_ambassador_invalid_rerenders_with_errors(client, valid_pro_data):
    response = client.post(reverse("create_work_ambassador"), data={**valid_pro_data, "email": ""})
    assert response.status_code == 200
    assert response.context["form"].errors
    messages = list(response.context["messages"])
    assert len(messages) > 0


def _training_ambassador_data(higher_ed_school_id, formation_pk, **overrides):
    return {
        "civility": "Madame",
        "first_name": "Manon",
        "last_name": "Desbordes",
        "email": "manon@example.com",
        "phone": "0612345678",
        "school_id": str(higher_ed_school_id),
        "formation_id": str(formation_pk),
        "terms_accepted": True,
        "manifeste_accepted": True,
        **overrides,
    }


@pytest.mark.django_db
def test_new_training_ambassador_get(client):
    assert client.get(reverse("new_training_ambassador")).status_code == 200


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_training_ambassador_valid_redirects(client, higher_ed_school, higher_ed_formation):
    response = client.post(
        reverse("create_training_ambassador"),
        data=_training_ambassador_data(higher_ed_school.id, higher_ed_formation.pk),
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_training_ambassador_valid_persists_student_pro_and_experience(
    client, higher_ed_school, higher_ed_formation
):
    from techpourtoutes.models import Pro

    client.post(
        reverse("create_training_ambassador"),
        data=_training_ambassador_data(higher_ed_school.id, higher_ed_formation.pk),
    )

    pro = Pro.objects.get(email="manon@example.com")
    assert "training_ambassador" in pro.engagements
    assert pro.professional_situation == "student"

    experience = pro.training_experiences.get()
    assert experience.school == higher_ed_school
    assert experience.formation == higher_ed_formation


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_training_ambassador_authenticated_pro_updates_pro(
    client, pro, higher_ed_school, higher_ed_formation
):
    from techpourtoutes.models import Pro

    client.force_login(pro)
    client.post(
        reverse("create_training_ambassador"),
        data=_training_ambassador_data(
            higher_ed_school.id, higher_ed_formation.pk, email=pro.email, first_name="Modifiée"
        ),
    )

    assert Pro.objects.count() == 1
    pro.refresh_from_db()
    assert pro.first_name == "Modifiée"
    assert "training_ambassador" in pro.engagements
    assert pro.training_experiences.get().school == higher_ed_school


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_new_training_ambassador_reports_a_missing_school(
    client, higher_ed_school, higher_ed_formation
):
    from django.core import mail

    from techpourtoutes.models import Pro

    response = client.post(
        reverse("create_training_ambassador"),
        data=_training_ambassador_data(
            higher_ed_school.id,
            higher_ed_formation.pk,
            school_id="",
            school_label="École du bout du monde",
            school_not_found="on",
        ),
    )

    assert response.status_code == 302
    experience = Pro.objects.get(email="manon@example.com").training_experiences.get()
    assert experience.school is None
    assert experience.formation == higher_ed_formation

    report = next(msg for msg in mail.outbox if msg.to == ["perfectible@techpourtoutes.io"])
    assert "École du bout du monde" in report.body


def _workshop_data(**overrides):
    return {
        "civility": "Madame",
        "first_name": "Manon",
        "last_name": "Desbordes",
        "email": "manon@example.com",
        "job_title": "Enseignante",
        "structure_uai": "0750001A",
        "school_label": "Lycée Voltaire",
        "postal_code": "75011",
        "remark": "",
        "ateliers": ["future_of_tech", "future_of_ia"],
        "terms_accepted": True,
        "manifeste_accepted": True,
        **overrides,
    }


@pytest.mark.django_db
def test_new_workshop_request_get(client):
    assert client.get(reverse("new_workshop_request")).status_code == 200


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_workshop_request_valid_creates_pro_and_enqueues_task(client):
    from techpourtoutes.models import Pro

    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task") as mock_task:
        response = client.post(reverse("create_workshop_request"), data=_workshop_data())

    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")

    pro = Pro.objects.get(email="manon@example.com")
    assert "workshops" in pro.engagements
    mock_task.delay.assert_called_once_with(
        pro_pk=str(pro.pk),
        ateliers=["future_of_tech", "future_of_ia"],
        remark="",
        structure_uai="0750001A",
    )


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_new_workshop_request_reports_a_missing_school_and_still_notifies_latitudes(client):
    from django.core import mail

    from techpourtoutes.models import Pro

    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task") as mock_task:
        response = client.post(
            reverse("create_workshop_request"),
            data=_workshop_data(
                structure_uai="",
                school_label="Lycée du bout du monde",
                postal_code="",
                school_not_found="on",
            ),
        )

    assert response.status_code == 302
    pro = Pro.objects.get(email="manon@example.com")
    assert pro.structure_name == "Lycée du bout du monde"
    mock_task.delay.assert_called_once_with(
        pro_pk=str(pro.pk),
        ateliers=["future_of_tech", "future_of_ia"],
        remark="",
        structure_uai="",
    )

    report = next(msg for msg in mail.outbox if msg.to == ["perfectible@techpourtoutes.io"])
    assert "Lycée du bout du monde" in report.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_workshop_request_with_consent_enables_brevo_sync(client):
    from techpourtoutes.models import Pro

    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task"):
        client.post(
            reverse("create_workshop_request"), data=_workshop_data(newsletter_consent=True)
        )

    assert Pro.objects.get(email="manon@example.com").brevo_sync_enabled is True


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_workshop_request_without_consent_leaves_brevo_sync_disabled(client):
    from techpourtoutes.models import Pro

    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task"):
        client.post(reverse("create_workshop_request"), data=_workshop_data())

    assert Pro.objects.get(email="manon@example.com").brevo_sync_enabled is False


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_workshop_request_valid_sends_welcome_email(client):
    from django.core import mail

    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task"):
        client.post(reverse("create_workshop_request"), data=_workshop_data())

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["manon@example.com"]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_workshop_request_valid_persists_one_request_per_type(client):
    from techpourtoutes.models import Pro, WorkshopRequest

    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task"):
        client.post(reverse("create_workshop_request"), data=_workshop_data(remark="Une note"))

    pro = Pro.objects.get(email="manon@example.com")
    requests = pro.workshop_requests.all()
    assert {r.type for r in requests} == {"future_of_tech", "future_of_ia"}
    assert all(r.remark == "Une note" for r in requests)
    assert WorkshopRequest.objects.count() == 2


@pytest.mark.django_db
def test_create_workshop_request_invalid_rerenders_with_errors(client):
    response = client.post(reverse("create_workshop_request"), data=_workshop_data(ateliers=[]))
    assert response.status_code == 200
    assert response.context["form"].errors
    messages = list(response.context["messages"])
    assert len(messages) > 0


@pytest.mark.django_db
def test_new_sponsor_get(client):
    assert client.get(reverse("new_sponsor")).status_code == 200


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_sponsor_valid_redirects(client, valid_pro_data):
    response = client.post(reverse("create_sponsor"), data=valid_pro_data)
    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")


@pytest.mark.django_db
def test_create_sponsor_invalid_rerenders_with_errors(client, valid_pro_data):
    response = client.post(reverse("create_sponsor"), data={**valid_pro_data, "email": ""})
    assert response.status_code == 200
    assert response.context["form"].errors
    messages = list(response.context["messages"])
    assert len(messages) > 0


# --- Authenticated pro: GET exposes pro in context ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    ["new_mentor", "new_work_ambassador", "new_workshop_request", "new_sponsor"],
)
def test_new_engagement_page_passes_authenticated_pro_to_context(client, pro, url_name):
    client.force_login(pro)
    response = client.get(reverse(url_name))
    assert response.status_code == 200
    assert response.context["pro"] == pro


@pytest.mark.django_db
def test_new_mentor_disables_email_for_authenticated_pro(client, pro):
    client.force_login(pro)
    html = client.get(reverse("new_mentor")).content.decode()
    assert _email_input_is_disabled(html)


@pytest.mark.django_db
def test_new_mentor_email_editable_for_anonymous(client):
    html = client.get(reverse("new_mentor")).content.decode()
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
        "manifeste_accepted": True,
        **overrides,
    }


@pytest.mark.django_db
def test_create_mentor_authenticated_pro_updates_pro(client, pro, mock_create_mentor):
    from techpourtoutes.models import Pro

    client.force_login(pro)
    client.post(reverse("create_mentor"), data=_pro_post_data(pro, first_name="Modifiée"))

    assert Pro.objects.count() == 1


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_work_ambassador_authenticated_pro_updates_pro(client, pro):
    client.force_login(pro)
    client.post(reverse("create_work_ambassador"), data=_pro_post_data(pro, first_name="Modifiée"))

    pro.refresh_from_db()
    assert pro.first_name == "Modifiée"
    assert "work_ambassador" in pro.engagements


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_new_work_ambassador_does_not_duplicate_existing_engagement(client, pro):
    pro.engagements = ["work_ambassador"]
    pro.save()
    client.force_login(pro)

    client.post(reverse("create_work_ambassador"), data=_pro_post_data(pro))

    pro.refresh_from_db()
    assert pro.engagements.count("work_ambassador") == 1


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_workshop_request_authenticated_pro_updates_pro(client, pro):
    client.force_login(pro)
    data = _workshop_data(email=pro.email, first_name="Modifiée")
    with patch("techpourtoutes.views.coalition_views.notify_workshop_request_task"):
        client.post(reverse("create_workshop_request"), data=data)

    pro.refresh_from_db()
    assert pro.first_name == "Modifiée"
    assert "workshops" in pro.engagements


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_sponsor_authenticated_pro_updates_pro(client, pro):
    client.force_login(pro)
    client.post(reverse("create_sponsor"), data=_pro_post_data(pro, first_name="Modifiée"))

    pro.refresh_from_db()
    assert pro.first_name == "Modifiée"
    assert "sponsor" in pro.engagements


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


# --- New pro receives welcome email ---


@pytest.mark.parametrize(
    "url_name",
    [
        "create_work_ambassador",
        "create_sponsor",
    ],
)
@pytest.mark.django_db
def test_new_pro_receives_welcome_email(client, valid_pro_data, url_name):
    from techpourtoutes.mailers import ProMailer

    with (
        patch.object(ProMailer, "engagement_added") as engagement_added,
        patch.object(ProMailer, "welcome") as welcome,
    ):
        response = client.post(
            reverse(url_name),
            data=valid_pro_data,
        )

    assert response.status_code == 302

    engagement_added.assert_not_called()
    welcome.assert_called_once()


@pytest.mark.django_db
def test_create_training_ambassador_new_pro_receives_welcome_email(
    client,
    higher_ed_school,
    higher_ed_formation,
):
    from techpourtoutes.mailers import ConsortiumMailer, ProMailer

    with (
        patch.object(
            ConsortiumMailer,
            "training_ambassador_signed_up",
        ) as training_ambassador_signed_up,
        patch.object(
            ProMailer,
            "engagement_added",
        ) as engagement_added,
        patch.object(
            ProMailer,
            "welcome_training_ambassador",
        ) as welcome_training_ambassador,
        patch.object(
            ProMailer,
            "welcome",
        ) as welcome,
    ):
        response = client.post(
            reverse("create_training_ambassador"),
            data=_training_ambassador_data(
                higher_ed_school.id,
                higher_ed_formation.pk,
            ),
        )

    assert response.status_code == 302

    training_ambassador_signed_up.assert_called_once()
    engagement_added.assert_not_called()
    welcome_training_ambassador.assert_called_once()
    welcome.assert_called_once()


@pytest.mark.django_db
def test_create_workshop_request_new_pro_receives_welcome_email(
    client,
):
    from techpourtoutes.mailers import ProMailer

    with (
        patch.object(
            ProMailer,
            "engagement_added",
        ) as engagement_added,
        patch.object(
            ProMailer,
            "welcome",
        ) as welcome,
        patch("techpourtoutes.views.coalition_views.notify_workshop_request_task") as mock_task,
    ):
        response = client.post(
            reverse("create_workshop_request"),
            data=_workshop_data(),
        )

    assert response.status_code == 302

    mock_task.delay.assert_called_once()
    engagement_added.assert_not_called()
    welcome.assert_called_once()


# --- Existing pro receives new engagement email ---


@pytest.mark.parametrize(
    "url_name",
    [
        "create_work_ambassador",
        "create_sponsor",
    ],
)
@pytest.mark.django_db
def test_existing_pro_receives_engagement_added_email(client, pro, url_name):
    from techpourtoutes.mailers import ProMailer

    client.force_login(pro)

    with (
        patch.object(ProMailer, "engagement_added") as engagement_added,
        patch.object(ProMailer, "welcome") as welcome,
    ):
        response = client.post(
            reverse(url_name),
            data=_pro_post_data(pro),
        )

    assert response.status_code == 302

    engagement_added.assert_called_once_with(pro=pro)
    welcome.assert_not_called()


@pytest.mark.django_db
def test_create_training_ambassador_existing_pro_receives_engagement_added_email(
    client,
    pro,
    higher_ed_school,
    higher_ed_formation,
):
    from techpourtoutes.mailers import ConsortiumMailer, ProMailer

    client.force_login(pro)

    with (
        patch.object(
            ConsortiumMailer,
            "training_ambassador_signed_up",
        ) as training_ambassador_signed_up,
        patch.object(
            ProMailer,
            "engagement_added",
        ) as engagement_added,
        patch.object(
            ProMailer,
            "welcome",
        ) as welcome,
    ):
        response = client.post(
            reverse("create_training_ambassador"),
            data=_training_ambassador_data(
                higher_ed_school.id,
                higher_ed_formation.pk,
                email=pro.email,
            ),
        )

    assert response.status_code == 302

    training_ambassador_signed_up.assert_called_once()
    engagement_added.assert_called_once()
    welcome.assert_not_called()


@pytest.mark.django_db
def test_create_workshop_request_existing_pro_receives_engagement_added_email(
    client,
    pro,
):
    from techpourtoutes.mailers import ProMailer

    client.force_login(pro)

    with (
        patch.object(
            ProMailer,
            "engagement_added",
        ) as engagement_added,
        patch.object(
            ProMailer,
            "welcome",
        ) as welcome,
        patch("techpourtoutes.views.coalition_views.notify_workshop_request_task") as mock_task,
    ):
        response = client.post(
            reverse("create_workshop_request"),
            data=_workshop_data(
                email=pro.email,
            ),
        )

    assert response.status_code == 302

    mock_task.delay.assert_called_once()
    engagement_added.assert_called_once()
    welcome.assert_not_called()
