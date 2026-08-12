from datetime import date
from urllib.parse import quote

import pytest
from django.core import mail
from django.test import override_settings
from waffle.testutils import override_switch

from techpourtoutes.models import Beneficiary, Level, User
from techpourtoutes.utils.school_year import (
    current_school_year_label,
    current_school_year_start_date,
    next_school_year_start_date,
    school_year_dates,
)

FUNNEL_URL = "/inscription/"


@pytest.fixture
def beneficiary_mode():
    with override_switch("beneficiary_mode", active=True):
        yield


def _valid_identity_post():
    return {
        "action": "identity",
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
def _answers(**overrides):
    return {
        "action": "training_experience",
        "email": "oceane@example.com",
        "first_name": "Océane",
        "last_name": "Durand",
        "birth_date": "2005-01-01",
        "age_eligibility_accepted": "on",
        "terms_accepted": "on",
        **overrides,
    }


def _higher_education_post(higher_ed_school, higher_ed_formation, **overrides):
    answers = _answers(
        study_status="higher_education",
        level="bac_3",
        school_id=str(higher_ed_school.pk),
        school_label=higher_ed_school.display_label,
        formation_id=str(higher_ed_formation.pk),
        formation_label=higher_ed_formation.name,
    )
    return answers | overrides


def _high_school_post(school, formation, **overrides):
    answers = _answers(
        study_status="high_school",
        level="terminale",
        school_label=school.location_label,
        school_id=str(school.pk),
        formation_id=str(formation.pk),
        formation_label=formation.name,
    )
    return answers | overrides


# Three school years back, so the label stays inside the offered window whatever the year is.
_DIPLOMA_YEAR = current_school_year_start_date().year - 3
DIPLOMA_PERIOD_LABEL = f"{_DIPLOMA_YEAR}-{_DIPLOMA_YEAR + 1}"


def _last_diploma_post(school, formation, **overrides):
    answers = _answers(
        study_status="finished",
        period_label=DIPLOMA_PERIOD_LABEL,
        level="terminale",
        school_label=school.location_label,
        school_id=str(school.pk),
        formation_id=str(formation.pk),
        formation_label=formation.name,
    )
    return answers | overrides


@pytest.mark.django_db
def test_get_renders_funnel_shell(client, beneficiary_mode):
    response = client.get(FUNNEL_URL)
    assert response.status_code == 200
    # The GET is a stateless shell; the step itself is fetched by the client via "resume".
    assert b'id="funnel-step"' in response.content
    assert b'x-data="beneficiaryFunnel"' in response.content
    assert b'"action": "resume"' in response.content


@pytest.mark.django_db
def test_resume_without_answers_renders_email_step(client, beneficiary_mode):
    response = client.post(FUNNEL_URL, {"action": "resume"})
    assert response.status_code == 200
    assert b'name="action" value="email"' in response.content


@pytest.mark.django_db
def test_resume_returns_furthest_reached_step_prefilled(client, beneficiary_mode):
    response = client.post(
        FUNNEL_URL,
        {
            "action": "resume",
            "email": "oceane@example.com",
            "first_name": "Océane",
            "last_name": "Durand",
            "birth_date": "2005-01-01",
        },
    )
    assert b'name="action" value="study_status"' in response.content
    assert "Océane".encode() in response.content


@pytest.mark.django_db
def test_resume_returns_to_the_study_status_when_it_is_unknown(client, beneficiary_mode):
    # The last screen is picked from the study status, so a forged one can't reach it.
    response = client.post(
        FUNNEL_URL,
        {
            "action": "resume",
            "email": "oceane@example.com",
            "first_name": "Océane",
            "last_name": "Durand",
            "birth_date": "2005-01-01",
            "study_status": "whatever",
        },
    )

    assert b'name="action" value="study_status"' in response.content


@pytest.mark.django_db
def test_email_step_advances_to_identity(client, beneficiary_mode):
    response = client.post(FUNNEL_URL, {"action": "email", "email": "oceane@example.com"})
    assert response.status_code == 200
    assert b'name="action" value="identity"' in response.content


@pytest.mark.django_db
def test_existing_email_redirects_to_login(client, beneficiary_mode):
    User.objects.create_user(
        username="taken@example.com",
        email="taken@example.com",
        password="irrelevant",
        first_name="Taken",
        last_name="User",
    )
    response = client.post(FUNNEL_URL, {"action": "email", "email": "taken@example.com"})
    assert "se-connecter" in response["HX-Redirect"]
    assert f"back={quote('/', safe='')}" in response["HX-Redirect"]
    # A dead-end too: the client must not keep answers it can never submit.
    assert "funnelReset" in response["HX-Trigger"]


@pytest.mark.django_db
def test_existing_pro_email_redirects_to_login_with_coalition_back(client, beneficiary_mode, pro):
    response = client.post(FUNNEL_URL, {"action": "email", "email": pro.email})
    assert "se-connecter" in response["HX-Redirect"]
    assert f"back={quote('/coalition/', safe='')}" in response["HX-Redirect"]


@pytest.mark.django_db
@pytest.mark.parametrize("age", [15, 20, 25])
def test_identity_step_advances_when_age_is_eligible(client, beneficiary_mode, age):
    response = client.post(FUNNEL_URL, _identity_post_for_age(age))
    assert b'name="action" value="study_status"' in response.content


@pytest.mark.django_db
def test_identity_step_shows_too_young_screen_below_15(client, beneficiary_mode):
    response = client.post(FUNNEL_URL, _identity_post_for_age(14))
    assert b'name="action" value="study_status"' not in response.content
    assert b"un peu de patience" in response.content
    # The terminal screen tells the client to wipe its stored answers.
    assert "funnelReset" in response["HX-Trigger"]


@pytest.mark.django_db
def test_identity_step_shows_too_old_screen_above_25(client, beneficiary_mode):
    response = client.post(FUNNEL_URL, _identity_post_for_age(26))
    assert b'name="action" value="study_status"' not in response.content
    assert b"Rejoindre la coalition" in response.content
    assert "funnelReset" in response["HX-Trigger"]


@pytest.mark.django_db
def test_identity_step_keeps_birth_date_when_form_is_invalid(client, beneficiary_mode):
    # <input type="date"> only accepts YYYY-MM-DD, so the re-rendered field must keep that format.
    birth_date = _birth_date_for_age(20)
    response = client.post(FUNNEL_URL, {**_identity_post_for_age(20), "terms_accepted": ""})

    assert b'name="action" value="identity"' in response.content
    assert f'value="{birth_date.isoformat()}"'.encode() in response.content


@pytest.mark.django_db
def test_study_status_step_offers_the_secondary_levels_to_a_high_schooler(
    client, beneficiary_mode
):
    response = client.post(
        FUNNEL_URL,
        {**_valid_identity_post(), "action": "study_status", "study_status": "high_school"},
    )
    assert b'name="action" value="training_experience"' in response.content
    assert b"En quelle classe es-tu ?" in response.content
    assert b"Terminale" in response.content
    assert b"Bac +5" not in response.content


@pytest.mark.django_db
def test_study_status_step_offers_the_higher_ed_levels_to_a_student(client, beneficiary_mode):
    response = client.post(
        FUNNEL_URL,
        {**_valid_identity_post(), "action": "study_status", "study_status": "higher_education"},
    )
    assert "Quel est ton niveau d&#x27;études actuel ?".encode() in response.content
    assert b"Bac +5" in response.content
    assert b"Terminale" not in response.content


@pytest.mark.django_db
def test_study_status_step_asks_a_graduate_about_her_last_diploma(client, beneficiary_mode):
    response = client.post(
        FUNNEL_URL,
        {**_valid_identity_post(), "action": "study_status", "study_status": "finished"},
    )
    content = response.content.decode()

    assert "En quelle année as-tu obtenu ton dernier diplôme ?" in content
    # The level decides which establishment list is offered, so it is asked before it.
    assert "Quel est le niveau de ton diplôme ?" in content
    # A diploma can't be obtained in a school year that hasn't started yet.
    next_start_year = next_school_year_start_date().year
    assert current_school_year_label() in content
    assert f"{next_start_year}-{next_start_year + 1}" not in content


@pytest.mark.django_db
def test_training_experience_step_creates_beneficiary_and_shows_code_screen(
    client, beneficiary_mode, higher_ed_school, higher_ed_formation
):
    response = client.post(
        FUNNEL_URL, _higher_education_post(higher_ed_school, higher_ed_formation)
    )

    assert b"Saisis le code" in response.content
    assert "funnelReset" in response["HX-Trigger"]
    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.first_name == "Océane"
    assert beneficiary.last_name == "Durand"
    assert str(beneficiary.birth_date) == "2005-01-01"
    assert beneficiary.civility == User.Civility.MADAME


@pytest.mark.django_db
def test_training_experience_step_creates_the_current_year_training(
    client, beneficiary_mode, higher_ed_school, higher_ed_formation
):
    client.post(FUNNEL_URL, _higher_education_post(higher_ed_school, higher_ed_formation))

    experience = Beneficiary.objects.get(email="oceane@example.com").training_experiences.get()
    assert experience.school == higher_ed_school
    assert experience.level == Level.BAC_3
    assert experience.formation == higher_ed_formation
    assert experience.start_date == current_school_year_start_date()


@pytest.mark.django_db
def test_training_experience_step_creates_the_training_of_a_high_schooler(
    client, beneficiary_mode, school, formation
):
    client.post(FUNNEL_URL, _high_school_post(school, formation))

    experience = Beneficiary.objects.get(email="oceane@example.com").training_experiences.get()
    assert experience.school == school
    assert experience.level == Level.TERMINALE
    assert experience.formation == formation
    assert experience.start_date == current_school_year_start_date()


@pytest.mark.django_db
@pytest.mark.parametrize("study_status", ["finished", "resuming"])
def test_training_experience_step_creates_the_training_of_a_graduate(
    client, beneficiary_mode, school, formation, study_status
):
    client.post(FUNNEL_URL, _last_diploma_post(school, formation, study_status=study_status))

    experience = Beneficiary.objects.get(email="oceane@example.com").training_experiences.get()
    assert experience.school == school
    assert experience.level == Level.TERMINALE
    assert experience.formation == formation
    assert (experience.start_date, experience.end_date) == school_year_dates(DIPLOMA_PERIOD_LABEL)


@pytest.mark.django_db
def test_training_experience_step_does_not_create_without_an_establishment(
    client, beneficiary_mode, school, formation
):
    response = client.post(FUNNEL_URL, _high_school_post(school, formation, school_id=""))

    assert b'name="action" value="training_experience"' in response.content
    assert "Sélectionnez un établissement valide.".encode() in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_a_missing_school_still_creates_the_account_and_reports_it(
    client, beneficiary_mode, school, formation
):
    client.post(
        FUNNEL_URL,
        _high_school_post(
            school,
            formation,
            school_id="",
            school_label="Lycée du bout du monde",
            school_not_found="on",
        ),
    )

    experience = Beneficiary.objects.get(email="oceane@example.com").training_experiences.get()
    assert experience.school is None
    assert experience.formation == formation
    assert experience.level == Level.TERMINALE

    report = next(msg for msg in mail.outbox if msg.to == ["perfectible@techpourtoutes.io"])
    assert "Lycée du bout du monde" in report.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_training_experience_step_sends_login_code_and_welcome_emails(
    client, beneficiary_mode, higher_ed_school, higher_ed_formation
):
    client.post(FUNNEL_URL, _higher_education_post(higher_ed_school, higher_ed_formation))

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

    response = client.post(
        FUNNEL_URL, {"action": "code", "email": beneficiary.email, "code": code}
    )

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
        FUNNEL_URL, {"action": "code", "email": beneficiary.email, "code": "000000"}
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

    response = client.post(FUNNEL_URL, {"action": "resend", "email": beneficiary.email})

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
    response = client.post(FUNNEL_URL, {"action": "resend", "email": "inconnue@example.com"})

    assert response.status_code == 200
    assert b"Saisis le code" in response.content
    assert mail.outbox == []


@pytest.mark.django_db
def test_training_experience_step_routes_back_to_furthest_invalid_step_with_error(
    client, beneficiary_mode, higher_ed_school, higher_ed_formation
):
    # Email and study status are fine, but the birth date is invalid: the user is sent back
    # to the identity step (the furthest-back screen that needs correcting), not to email.
    response = client.post(
        FUNNEL_URL,
        _higher_education_post(higher_ed_school, higher_ed_formation, birth_date="not-a-date"),
    )

    assert b'name="action" value="identity"' in response.content
    assert "Certaines informations sont incomplètes ou invalides".encode() in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_training_experience_step_does_not_create_when_email_is_missing(
    client, beneficiary_mode, higher_ed_school, higher_ed_formation
):
    response = client.post(
        FUNNEL_URL, _higher_education_post(higher_ed_school, higher_ed_formation, email="")
    )

    assert response.status_code == 200
    assert b'name="action" value="email"' in response.content
    assert b"Ton adresse mail n" in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_back_step_returns_previous_step_prefilled(client, beneficiary_mode):
    response = client.post(
        FUNNEL_URL, {**_identity_post_for_age(20), "action": "back", "to": "study_status"}
    )
    assert b'name="action" value="identity"' in response.content
    assert "Océane".encode() in response.content
    assert f'value="{_birth_date_for_age(20).isoformat()}"'.encode() in response.content
