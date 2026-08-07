from datetime import date
from urllib.parse import quote

import pytest
from django.core import mail
from django.test import override_settings
from waffle.testutils import override_switch

from techpourtoutes.models import Beneficiary, User

FUNNEL_URL = "/inscription/"


@pytest.fixture
def beneficiary_mode():
    with override_switch("beneficiary_mode", active=True):
        yield


def _valid_identity_post():
    return {
        "step": "identity",
        "email": "oceane@example.com",
        "first_name": "Océane",
        "last_name": "Durand",
        "birth_date": "01/01/2005",
        "age_eligibility_accepted": "on",
        "terms_accepted": "on",
    }


def _birth_date_for_age(age):
    today = date.today()
    try:
        return today.replace(year=today.year - age)
    except ValueError:  # 29 February
        return today.replace(year=today.year - age, day=28)


def _identity_post_for_age(age):
    return {**_valid_identity_post(), "birth_date": _birth_date_for_age(age).isoformat()}


# The client is stateless: each POST carries the whole set of answers accumulated so far
# (this is what the Alpine/sessionStorage front-end injects into every request).
def _details_post(**overrides):
    data = {
        "step": "details",
        "email": "oceane@example.com",
        "first_name": "Océane",
        "last_name": "Durand",
        "birth_date": "2005-01-01",
        "age_eligibility_accepted": "on",
        "terms_accepted": "on",
        "study_status": "higher_education",
        "detail_1": "M2",
        "detail_2": "Sorbonne",
        "detail_3": "Info",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_get_renders_funnel_shell(client, beneficiary_mode):
    response = client.get(FUNNEL_URL)
    assert response.status_code == 200
    # The GET is a stateless shell; the step itself is fetched by the client via "resume".
    assert b'id="funnel-step"' in response.content
    assert b'x-data="beneficiaryFunnel"' in response.content
    assert b'"step": "resume"' in response.content


@pytest.mark.django_db
def test_resume_without_answers_renders_email_step(client, beneficiary_mode):
    response = client.post(FUNNEL_URL, {"step": "resume"})
    assert response.status_code == 200
    assert b'name="step" value="email"' in response.content


@pytest.mark.django_db
def test_resume_returns_furthest_reached_step_prefilled(client, beneficiary_mode):
    response = client.post(
        FUNNEL_URL,
        {
            "step": "resume",
            "email": "oceane@example.com",
            "first_name": "Océane",
            "last_name": "Durand",
            "birth_date": "2005-01-01",
        },
    )
    assert b'name="step" value="study_status"' in response.content
    assert "Océane".encode() in response.content


@pytest.mark.django_db
def test_email_step_advances_to_identity(client, beneficiary_mode):
    response = client.post(FUNNEL_URL, {"step": "email", "email": "oceane@example.com"})
    assert response.status_code == 200
    assert b'name="step" value="identity"' in response.content


@pytest.mark.django_db
def test_existing_email_redirects_to_login(client, beneficiary_mode):
    User.objects.create_user(
        username="taken@example.com",
        email="taken@example.com",
        password="irrelevant",
        first_name="Taken",
        last_name="User",
    )
    response = client.post(FUNNEL_URL, {"step": "email", "email": "taken@example.com"})
    assert "se-connecter" in response["HX-Redirect"]
    assert f"back={quote('/', safe='')}" in response["HX-Redirect"]
    # A dead-end too: the client must not keep answers it can never submit.
    assert "funnelReset" in response["HX-Trigger"]


@pytest.mark.django_db
def test_existing_pro_email_redirects_to_login_with_coalition_back(client, beneficiary_mode, pro):
    response = client.post(FUNNEL_URL, {"step": "email", "email": pro.email})
    assert "se-connecter" in response["HX-Redirect"]
    assert f"back={quote('/coalition/', safe='')}" in response["HX-Redirect"]


@pytest.mark.django_db
@pytest.mark.parametrize("age", [15, 20, 25])
def test_identity_step_advances_when_age_is_eligible(client, beneficiary_mode, age):
    response = client.post(FUNNEL_URL, _identity_post_for_age(age))
    assert b'name="step" value="study_status"' in response.content


@pytest.mark.django_db
def test_identity_step_shows_too_young_screen_below_15(client, beneficiary_mode):
    response = client.post(FUNNEL_URL, _identity_post_for_age(14))
    assert b'name="step" value="study_status"' not in response.content
    assert b"un peu de patience" in response.content
    # The terminal screen tells the client to wipe its stored answers.
    assert "funnelReset" in response["HX-Trigger"]


@pytest.mark.django_db
def test_identity_step_shows_too_old_screen_above_25(client, beneficiary_mode):
    response = client.post(FUNNEL_URL, _identity_post_for_age(26))
    assert b'name="step" value="study_status"' not in response.content
    assert b"Rejoindre la coalition" in response.content
    assert "funnelReset" in response["HX-Trigger"]


@pytest.mark.django_db
def test_identity_step_keeps_birth_date_when_form_is_invalid(client, beneficiary_mode):
    # <input type="date"> only accepts YYYY-MM-DD, so the re-rendered field must keep that format.
    birth_date = _birth_date_for_age(20)
    response = client.post(FUNNEL_URL, {**_identity_post_for_age(20), "terms_accepted": ""})

    assert b'name="step" value="identity"' in response.content
    assert f'value="{birth_date.isoformat()}"'.encode() in response.content


@pytest.mark.django_db
def test_study_status_step_renders_details_for_the_chosen_status(client, beneficiary_mode):
    response = client.post(
        FUNNEL_URL,
        {**_valid_identity_post(), "step": "study_status", "study_status": "middle_high_school"},
    )
    assert b'name="step" value="details"' in response.content
    assert b"En quelle classe es-tu ?" in response.content


@pytest.mark.django_db
def test_details_step_creates_beneficiary_and_shows_code_screen(client, beneficiary_mode):
    response = client.post(FUNNEL_URL, _details_post())

    assert b"Saisis le code" in response.content
    assert "funnelReset" in response["HX-Trigger"]
    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.first_name == "Océane"
    assert beneficiary.last_name == "Durand"
    assert str(beneficiary.birth_date) == "2005-01-01"
    assert beneficiary.civility == User.Civility.MADAME
    # detail inputs are wireframe-only and must not be persisted anywhere
    assert not hasattr(beneficiary, "detail_1")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_details_step_sends_login_code_and_welcome_emails(client, beneficiary_mode):
    client.post(FUNNEL_URL, _details_post())

    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.login_code_hash != ""

    assert len(mail.outbox) == 2
    subjects = {message.subject for message in mail.outbox}
    assert "Ton code de connexion à TechPourToutes" in subjects
    assert "Bienvenue au club" in subjects
    for message in mail.outbox:
        assert message.to == [beneficiary.email]


@pytest.mark.django_db
def test_funnel_redirects_authenticated_user_to_account(client, beneficiary_mode):
    beneficiary = Beneficiary.objects.create(
        username="oceane@example.com",
        email="oceane@example.com",
        first_name="Océane",
        last_name="Durand",
    )
    client.force_login(beneficiary)

    response = client.get(FUNNEL_URL)

    assert response.status_code == 302
    assert response["Location"] == "/mon-compte/"


@pytest.mark.django_db
def test_code_step_with_valid_code_logs_in_and_redirects(client, beneficiary_mode):
    beneficiary = Beneficiary.objects.create(
        username="oceane@example.com",
        email="oceane@example.com",
        first_name="Océane",
        last_name="Durand",
    )
    code = beneficiary.issue_login_code()

    response = client.post(FUNNEL_URL, {"step": "code", "email": beneficiary.email, "code": code})

    assert response["HX-Redirect"] == "/mon-compte/"
    assert client.session.get("_auth_user_id") == str(beneficiary.pk)


@pytest.mark.django_db
def test_code_step_with_invalid_code_shows_error(client, beneficiary_mode):
    beneficiary = Beneficiary.objects.create(
        username="oceane@example.com",
        email="oceane@example.com",
        first_name="Océane",
        last_name="Durand",
    )
    beneficiary.issue_login_code()

    response = client.post(
        FUNNEL_URL, {"step": "code", "email": beneficiary.email, "code": "000000"}
    )

    assert response.status_code == 200
    assert b"Saisis le code" in response.content
    assert "Code invalide ou expiré".encode() in response.content
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_resend_step_mails_a_new_code_and_stays_on_the_code_screen(client, beneficiary_mode):
    beneficiary = Beneficiary.objects.create(
        username="oceane@example.com",
        email="oceane@example.com",
        first_name="Océane",
        last_name="Durand",
    )
    beneficiary.issue_login_code()
    previous_hash = beneficiary.login_code_hash

    response = client.post(FUNNEL_URL, {"step": "resend", "email": beneficiary.email})

    assert response.status_code == 200
    assert b"Saisis le code" in response.content
    assert "a été envoyé par mail.".encode() in response.content
    beneficiary.refresh_from_db()
    assert beneficiary.login_code_hash != previous_hash
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Ton code de connexion à TechPourToutes"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_resend_step_with_unknown_email_sends_nothing(client, beneficiary_mode):
    response = client.post(FUNNEL_URL, {"step": "resend", "email": "inconnue@example.com"})

    assert response.status_code == 200
    assert b"Saisis le code" in response.content
    assert mail.outbox == []


@pytest.mark.django_db
def test_details_step_routes_back_to_furthest_invalid_step_with_error(client, beneficiary_mode):
    # Email and study status are fine, but the birth date is invalid: the user is sent back
    # to the identity step (the furthest-back screen that needs correcting), not to email.
    response = client.post(FUNNEL_URL, _details_post(birth_date="not-a-date"))

    assert b'name="step" value="identity"' in response.content
    assert "Certaines informations sont incomplètes ou invalides".encode() in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_details_step_does_not_create_when_email_is_missing(client, beneficiary_mode):
    response = client.post(FUNNEL_URL, _details_post(email=""))

    assert response.status_code == 200
    assert b'name="step" value="email"' in response.content
    assert b"Ton adresse mail n" in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_back_step_returns_previous_step_prefilled(client, beneficiary_mode):
    response = client.post(
        FUNNEL_URL, {**_identity_post_for_age(20), "step": "back", "to": "study_status"}
    )
    assert b'name="step" value="identity"' in response.content
    assert "Océane".encode() in response.content
    assert f'value="{_birth_date_for_age(20).isoformat()}"'.encode() in response.content
