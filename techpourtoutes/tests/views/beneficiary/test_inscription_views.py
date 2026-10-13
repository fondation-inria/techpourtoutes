from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from techpourtoutes.models import Beneficiary, Level, User
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.utils.funnel import FunnelSession
from techpourtoutes.utils.school_year import (
    current_school_year_label,
    current_school_year_start_date,
    next_school_year_start_date,
    school_year_dates,
)

FUNNEL_URL = "/inscription/"
NEW_FUNNEL_URL = "/inscription/new/"


_EMAIL = {"email": "oceane@example.com"}
_IDENTITY = {
    "first_name": "Océane",
    "last_name": "Durand",
    "birth_date": "2005-01-01",
    "age_eligibility_accepted": "on",
    "terms_accepted": "on",
}


def _funnel(client):
    return FunnelSession(SimpleNamespace(session=client.session), "inscription_funnel")


# Starts the funnel midway, as if she had already answered `steps`.
def _seed_funnel(client, *, current, values=None, **steps):
    session = client.session
    funnel = FunnelSession(SimpleNamespace(session=session), "inscription_funnel")
    funnel.update(**(values or {}))
    for step, data in steps.items():
        funnel.save_step(step, data)
    funnel.current_step = current
    session.save()


def _seed_until_training(
    client, study_status, *, current="training_experience", email=_EMAIL, identity=None, **kwargs
):
    _seed_funnel(
        client,
        current=current,
        email=email,
        identity=_IDENTITY | (identity or {}),
        study_status={"study_status": study_status},
        **kwargs,
    )


def _post_step(client, step, data=None):
    return client.post(FUNNEL_URL, {"action": step, **(data or {})})


def _identity_for_age(age):
    return {**_IDENTITY, "birth_date": _birth_date_for_age(age).isoformat()}


def _birth_date_for_age(age):
    today = date.today()
    try:
        return today.replace(year=today.year - age)
    except ValueError:  # 29 February
        return today.replace(year=today.year - age, day=28)


def _higher_education_training(higher_ed_school, higher_ed_formation, **overrides):
    return {
        "level": "bac_3",
        "school_id": str(higher_ed_school.pk),
        "school_label": higher_ed_school.display_label,
        "formation_id": str(higher_ed_formation.pk),
        "formation_label": higher_ed_formation.name,
        **overrides,
    }


def _high_school_training(school, formation, **overrides):
    return {
        "level": "terminale",
        "school_label": school.location_label,
        "school_id": str(school.pk),
        "formation_id": str(formation.pk),
        "formation_label": formation.name,
        **overrides,
    }


# Three school years back, so the label stays inside the offered window whatever the year is.
_DIPLOMA_YEAR = current_school_year_start_date().year - 3
DIPLOMA_PERIOD_LABEL = f"{_DIPLOMA_YEAR}-{_DIPLOMA_YEAR + 1}"


def _last_diploma_training(school, formation):
    return {
        "period_label": DIPLOMA_PERIOD_LABEL,
        "level": "terminale",
        "school_label": school.location_label,
        "school_id": str(school.pk),
        "formation_id": str(formation.pk),
        "formation_label": formation.name,
    }


# She answered every screen up to the optional ones, which `values` ask for.
def _seed_after_training(client, higher_ed_school, higher_ed_formation, *, current, **kwargs):
    _seed_until_training(
        client,
        "higher_education",
        current=current,
        training_experience=_higher_education_training(higher_ed_school, higher_ed_formation),
        **kwargs,
    )


@pytest.mark.django_db
def test_get_renders_the_email_step_of_a_fresh_funnel(client):
    response = client.get(FUNNEL_URL)

    assert response.status_code == 200
    assert b'id="funnel-step"' in response.content
    assert b'name="action" value="email"' in response.content


@pytest.mark.django_db
def test_get_resumes_on_the_current_step_prefilled(client):
    _seed_funnel(client, current="identity", email=_EMAIL, identity=_IDENTITY)

    response = client.get(FUNNEL_URL)

    assert b'name="action" value="identity"' in response.content
    assert "Océane".encode() in response.content


@pytest.mark.django_db
def test_a_valid_step_is_the_one_a_reload_resumes_after(client):
    _post_step(client, "email", _EMAIL)

    assert b'name="action" value="identity"' in client.get(FUNNEL_URL).content


@pytest.mark.django_db
def test_an_invalid_step_saves_nothing(client):
    _post_step(client, "email", {"email": "pas-un-email"})

    assert _funnel(client).answers.get("email") is None


@pytest.mark.django_db
def test_a_submitted_screen_replaces_its_previous_answers(client):
    _seed_funnel(
        client,
        current="identity",
        email=_EMAIL,
        identity={**_IDENTITY, "newsletter_consent": "on"},
    )

    _post_step(client, "identity", _IDENTITY)

    assert "newsletter_consent" not in _funnel(client).answers


@pytest.mark.django_db
def test_new_inscription_funnel_redirects_to_the_funnel(client):
    response = client.get(NEW_FUNNEL_URL)

    assert response.status_code == 302
    assert response["Location"] == FUNNEL_URL


@pytest.mark.django_db
def test_new_inscription_funnel_starts_over(client):
    _seed_funnel(
        client,
        current="identity",
        values={"wants_training_ambassador": True},
        email=_EMAIL,
        identity=_IDENTITY,
    )

    client.get(NEW_FUNNEL_URL)

    assert _funnel(client).current_step is None
    assert "email" not in _funnel(client).answers
    assert _funnel(client).answers["wants_training_ambassador"] is False
    assert b'name="action" value="email"' in client.get(FUNNEL_URL).content


@pytest.mark.django_db
@pytest.mark.parametrize(("query", "flag"), [("", False), ("?wants_mentor=1", True)])
def test_new_inscription_funnel_records_whether_a_mentor_is_wanted(client, query, flag):
    client.get(f"{NEW_FUNNEL_URL}{query}")

    assert _funnel(client).answers["wants_mentor"] is flag


@pytest.mark.django_db
def test_reloading_the_funnel_keeps_progress_and_what_she_came_for(client):
    client.get(f"{NEW_FUNNEL_URL}?wants_mentor=1")
    _post_step(client, "email", _EMAIL)

    response = client.get(FUNNEL_URL)

    assert b'name="action" value="identity"' in response.content
    assert _funnel(client).answers["wants_mentor"] is True


@pytest.mark.django_db
def test_new_inscription_funnel_redirects_authenticated_user_to_account(client, beneficiary):
    client.force_login(beneficiary)

    response = client.get(NEW_FUNNEL_URL)

    assert response["Location"] == reverse("show_account")


_LOST_PROGRESS = "Ton inscription a expiré ou a été recommencée dans un autre onglet"


def _expire_funnel(client):
    session = client.session
    state = session["inscription_funnel"]
    state["updated_at"] = (timezone.now() - timedelta(hours=2)).isoformat()
    session["inscription_funnel"] = state
    session.save()


@pytest.mark.django_db
def test_a_screen_sent_after_the_funnel_restarted_elsewhere_starts_over_with_a_message(
    client, higher_ed_school, higher_ed_formation
):
    _seed_until_training(client, "higher_education")
    client.get(NEW_FUNNEL_URL)

    response = _post_step(
        client,
        "training_experience",
        _higher_education_training(higher_ed_school, higher_ed_formation),
    )

    assert b'name="action" value="email"' in response.content
    assert _LOST_PROGRESS.encode() in response.content
    assert "None" not in response.content.decode()
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_a_screen_sent_after_the_funnel_expired_starts_over_with_a_message(client):
    _seed_funnel(client, current="study_status", email=_EMAIL, identity=_IDENTITY)
    _expire_funnel(client)

    response = _post_step(client, "study_status", {"study_status": "higher_education"})

    assert b'name="action" value="email"' in response.content
    assert _LOST_PROGRESS.encode() in response.content
    assert _funnel(client).answered == set()


@pytest.mark.django_db
def test_a_screen_sent_without_an_earlier_one_goes_back_to_the_first_missing(client):
    _seed_funnel(client, current="study_status", email=_EMAIL)

    response = _post_step(client, "study_status", {"study_status": "higher_education"})

    assert b'name="action" value="identity"' in response.content
    assert _LOST_PROGRESS.encode() in response.content
    assert "study_status" not in _funnel(client).answered


@pytest.mark.django_db
def test_skipping_after_the_funnel_restarted_elsewhere_starts_over_with_a_message(
    client, higher_ed_school, higher_ed_formation
):
    _seed_after_training(
        client,
        higher_ed_school,
        higher_ed_formation,
        current="mentoring_signup",
        values={"wants_mentor": True},
    )
    client.get(NEW_FUNNEL_URL)

    response = _post_step(client, "skip", {"step": "mentoring_signup"})

    assert b'name="action" value="email"' in response.content
    assert _LOST_PROGRESS.encode() in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_going_back_after_the_funnel_restarted_elsewhere_starts_over_with_a_message(client):
    _seed_funnel(client, current="study_status", email=_EMAIL, identity=_IDENTITY)
    client.get(NEW_FUNNEL_URL)

    response = client.post(FUNNEL_URL, {"action": "back"})

    assert b'name="action" value="email"' in response.content
    assert _LOST_PROGRESS.encode() in response.content


@pytest.mark.django_db
def test_email_step_advances_to_identity(client):
    response = _post_step(client, "email", _EMAIL)
    assert response.status_code == 200
    assert b'name="action" value="identity"' in response.content


@pytest.mark.django_db
def test_existing_email_redirects_to_login(client):
    User.objects.create_user(
        username="taken@example.com",
        email="taken@example.com",
        password="irrelevant",
        first_name="Taken",
        last_name="User",
    )
    client.get(FUNNEL_URL)

    response = _post_step(client, "email", {"email": "taken@example.com"})

    assert "se-connecter" in response["HX-Redirect"]
    assert f"back={quote('/', safe='')}" in response["HX-Redirect"]
    assert f"next={quote('/', safe='')}" in response["HX-Redirect"]
    # A dead-end too: no point keeping answers she can never submit.
    assert _funnel(client).answers == {}


@pytest.mark.django_db
def test_existing_pro_email_redirects_to_login_with_coalition_back(client, pro):
    response = _post_step(client, "email", {"email": pro.email})
    assert "se-connecter" in response["HX-Redirect"]
    assert f"back={quote('/coalition/', safe='')}" in response["HX-Redirect"]
    assert f"next={quote('/coalition/', safe='')}" in response["HX-Redirect"]


@pytest.mark.django_db
def test_existing_registered_beneficiary_email_with_wants_mentor_logs_in_to_account(
    client, beneficiary
):
    beneficiary.jobirl_user_id = 42
    beneficiary.save()
    client.get(f"{NEW_FUNNEL_URL}?wants_mentor=1")

    response = _post_step(client, "email", {"email": beneficiary.email})

    assert "se-connecter" in response["HX-Redirect"]
    assert f"back={quote('/', safe='')}" in response["HX-Redirect"]
    assert f"next={quote(reverse('show_account'), safe='')}" in response["HX-Redirect"]


@pytest.mark.django_db
def test_existing_unregistered_beneficiary_email_with_wants_mentor_logs_in_to_mentoring_funnel(
    client, beneficiary
):
    client.get(f"{NEW_FUNNEL_URL}?wants_mentor=1")

    response = _post_step(client, "email", {"email": beneficiary.email})

    assert "se-connecter" in response["HX-Redirect"]
    assert f"back={quote('/', safe='')}" in response["HX-Redirect"]
    assert f"next={quote('/devenir-mentoree/', safe='')}" in response["HX-Redirect"]


@pytest.mark.django_db
def test_existing_beneficiary_email_with_wants_training_ambassador_logs_in_to_the_request(
    client, beneficiary
):
    client.get(f"{NEW_FUNNEL_URL}?wants_training_ambassador=1")

    response = _post_step(client, "email", {"email": beneficiary.email})

    next_url = reverse("new_training_ambassador_request")
    assert f"next={quote(next_url, safe='')}" in response["HX-Redirect"]


@pytest.mark.django_db
def test_existing_beneficiary_email_who_already_requested_a_training_ambassador_logs_in_to_account(
    client, beneficiary
):
    beneficiary.has_requested_training_ambassador = True
    beneficiary.save()
    client.get(f"{NEW_FUNNEL_URL}?wants_training_ambassador=1")

    response = _post_step(client, "email", {"email": beneficiary.email})

    assert f"next={quote(reverse('show_account'), safe='')}" in response["HX-Redirect"]


@pytest.mark.django_db
def test_existing_beneficiary_email_without_wants_mentor_redirects_to_home_back(
    client, beneficiary
):
    response = _post_step(client, "email", {"email": beneficiary.email})

    assert "se-connecter" in response["HX-Redirect"]
    assert f"back={quote('/', safe='')}" in response["HX-Redirect"]
    assert f"next={quote('/', safe='')}" in response["HX-Redirect"]


@pytest.mark.django_db
@pytest.mark.parametrize("age", [15, 20, 25])
def test_identity_step_advances_when_age_is_eligible(client, age):
    _seed_funnel(client, current="identity", email=_EMAIL)

    response = _post_step(client, "identity", _identity_for_age(age))
    assert b'name="action" value="study_status"' in response.content


@pytest.mark.django_db
def test_identity_step_shows_too_young_screen_below_15(client):
    _seed_funnel(client, current="identity", email=_EMAIL)

    response = _post_step(client, "identity", _identity_for_age(14))

    assert b'name="action" value="study_status"' not in response.content
    assert b"un peu de patience" in response.content
    assert _funnel(client).answers == {}


@pytest.mark.django_db
def test_identity_step_shows_too_old_screen_above_25(client):
    _seed_funnel(client, current="identity", email=_EMAIL)

    response = _post_step(client, "identity", _identity_for_age(26))

    assert b'name="action" value="study_status"' not in response.content
    assert b"Rejoindre la coalition" in response.content
    assert _funnel(client).answers == {}


@pytest.mark.django_db
def test_identity_step_keeps_birth_date_when_form_is_invalid(client):
    # <input type="date"> only accepts YYYY-MM-DD, so the re-rendered field must keep that format.
    birth_date = _birth_date_for_age(20)
    _seed_funnel(client, current="identity", email=_EMAIL)

    response = _post_step(client, "identity", {**_identity_for_age(20), "terms_accepted": ""})

    assert b'name="action" value="identity"' in response.content
    assert f'value="{birth_date.isoformat()}"'.encode() in response.content


@pytest.mark.django_db
def test_study_status_step_offers_the_secondary_levels_to_a_high_schooler(client):
    _seed_funnel(client, current="study_status", email=_EMAIL, identity=_IDENTITY)

    response = _post_step(client, "study_status", {"study_status": "high_school"})
    assert b'name="action" value="training_experience"' in response.content
    assert b"En quelle classe es-tu ?" in response.content
    assert b"Terminale" in response.content
    assert b"Bac +5" not in response.content


@pytest.mark.django_db
def test_study_status_step_offers_the_higher_ed_levels_to_a_student(client):
    _seed_funnel(client, current="study_status", email=_EMAIL, identity=_IDENTITY)

    response = _post_step(client, "study_status", {"study_status": "higher_education"})
    assert "Quel est ton niveau d&#x27;études actuel ?".encode() in response.content
    assert b"Bac +5" in response.content
    assert b"Terminale" not in response.content


@pytest.mark.django_db
def test_study_status_step_asks_a_graduate_about_her_last_diploma(client):
    _seed_funnel(client, current="study_status", email=_EMAIL, identity=_IDENTITY)

    response = _post_step(client, "study_status", {"study_status": "finished"})
    content = response.content.decode()

    assert "En quelle année était-ce ?" in content
    # The level decides which establishment list is offered, so it is asked before it.
    assert "Quelle est la dernière année d&#x27;études que tu as validée ?" in content
    # A diploma can't be obtained in a school year that hasn't started yet.
    next_start_year = next_school_year_start_date().year
    assert current_school_year_label() in content
    assert f"{next_start_year}-{next_start_year + 1}" not in content


@pytest.mark.django_db
def test_training_experience_step_creates_beneficiary_and_shows_code_screen(
    client, higher_ed_school, higher_ed_formation
):
    _seed_until_training(client, "higher_education")

    response = _post_step(
        client,
        "training_experience",
        _higher_education_training(higher_ed_school, higher_ed_formation),
    )

    assert b"Saisis le code" in response.content
    assert _funnel(client).answers == {}
    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.first_name == "Océane"
    assert beneficiary.last_name == "Durand"
    assert str(beneficiary.birth_date) == "2005-01-01"
    assert beneficiary.civility == User.Civility.MADAME


@pytest.mark.django_db
def test_training_experience_step_creates_the_current_year_training(
    client, higher_ed_school, higher_ed_formation
):
    _seed_until_training(client, "higher_education")

    _post_step(
        client,
        "training_experience",
        _higher_education_training(higher_ed_school, higher_ed_formation),
    )

    experience = Beneficiary.objects.get(email="oceane@example.com").training_experiences.get()
    assert experience.school == higher_ed_school
    assert experience.level == Level.BAC_3
    assert experience.formation == higher_ed_formation
    assert experience.start_date == current_school_year_start_date()


@pytest.mark.django_db
def test_training_experience_step_creates_the_training_of_a_high_schooler(
    client, school, formation
):
    _seed_until_training(client, "high_school")

    _post_step(client, "training_experience", _high_school_training(school, formation))

    experience = Beneficiary.objects.get(email="oceane@example.com").training_experiences.get()
    assert experience.school == school
    assert experience.level == Level.TERMINALE
    assert experience.formation == formation
    assert experience.start_date == current_school_year_start_date()


@pytest.mark.django_db
@pytest.mark.parametrize("study_status", ["finished", "resuming"])
def test_training_experience_step_creates_the_training_of_a_graduate(
    client, school, formation, study_status
):
    _seed_until_training(client, study_status)

    _post_step(client, "training_experience", _last_diploma_training(school, formation))

    experience = Beneficiary.objects.get(email="oceane@example.com").training_experiences.get()
    assert experience.school == school
    assert experience.level == Level.TERMINALE
    assert experience.formation == formation
    assert (experience.start_date, experience.end_date) == school_year_dates(DIPLOMA_PERIOD_LABEL)


@pytest.mark.django_db
def test_training_experience_step_does_not_create_without_an_establishment(
    client, school, formation
):
    _seed_until_training(client, "high_school")

    response = _post_step(
        client, "training_experience", _high_school_training(school, formation, school_id="")
    )

    assert b'name="action" value="training_experience"' in response.content
    assert "Sélectionnez un établissement valide.".encode() in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_a_missing_school_still_creates_the_account_and_reports_it(client, school, formation):
    _seed_until_training(client, "high_school")

    _post_step(
        client,
        "training_experience",
        _high_school_training(
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
    client, higher_ed_school, higher_ed_formation
):
    _seed_until_training(client, "higher_education")

    _post_step(
        client,
        "training_experience",
        _higher_education_training(higher_ed_school, higher_ed_formation),
    )

    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.login_code_hash != ""

    assert len(mail.outbox) == 2
    subjects = {message.subject for message in mail.outbox}
    assert "Ton code de connexion à TechPourToutes" in subjects
    assert "Bienvenue au club" in subjects
    for message in mail.outbox:
        assert message.to == [beneficiary.email]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_skipping_the_mentoring_screen_creates_beneficiary_without_mentoring_signup(
    client, higher_ed_school, higher_ed_formation
):
    _seed_after_training(
        client,
        higher_ed_school,
        higher_ed_formation,
        current="mentoring_signup",
        values={"wants_mentor": True},
    )

    response = _post_step(client, "skip", {"step": "mentoring_signup"})

    assert b"Saisis le code" in response.content
    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.phone == ""
    subjects = {message.subject for message in mail.outbox}
    assert "Nouvelle attestation à envoyer" not in subjects


@pytest.mark.django_db
def test_skipping_the_mentoring_screen_leads_to_the_training_ambassador_request_when_wanted(
    client, higher_ed_school, higher_ed_formation
):
    _seed_after_training(
        client,
        higher_ed_school,
        higher_ed_formation,
        current="mentoring_signup",
        values={"wants_mentor": True, "wants_training_ambassador": True},
    )

    response = _post_step(client, "skip", {"step": "mentoring_signup"})

    assert b'name="action" value="training_ambassador_request"' in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_skipping_a_step_that_cannot_be_skipped_starts_over(client):
    _seed_funnel(client, current="identity", email=_EMAIL)

    response = _post_step(client, "skip", {"step": "identity"})

    assert b'name="action" value="email"' in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_show_skip_inscription_step_modal_submits_the_skipped_mentoring_screen(client):
    response = client.get(reverse("show_skip_inscription_step_modal", args=["mentoring_signup"]))

    assert b'name="action" value="skip"' in response.content
    assert b'name="step" value="mentoring_signup"' in response.content


@pytest.mark.django_db
def test_training_experience_step_leads_to_the_training_ambassador_request_when_one_is_wanted(
    client, higher_ed_school, higher_ed_formation
):
    _seed_until_training(client, "higher_education", values={"wants_training_ambassador": True})

    response = _post_step(
        client,
        "training_experience",
        _higher_education_training(higher_ed_school, higher_ed_formation),
    )

    assert b'name="action" value="training_ambassador_request"' in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_training_ambassador_request_step_creates_beneficiary_and_mails_the_topic(
    client, higher_ed_school, higher_ed_formation
):
    _seed_after_training(
        client,
        higher_ed_school,
        higher_ed_formation,
        current="training_ambassador_request",
        values={"wants_training_ambassador": True},
    )

    response = _post_step(
        client, "training_ambassador_request", {"topic": "Parcoursup et la vie sur le campus"}
    )

    assert b"Saisis le code" in response.content
    assert Beneficiary.objects.get(email="oceane@example.com").has_requested_training_ambassador
    [request_mail] = [
        message
        for message in mail.outbox
        if message.subject == "Nouvelle demande pour parler à une ambassadrice"
    ]
    assert "Parcoursup et la vie sur le campus" in request_mail.body


@pytest.mark.django_db
def test_training_ambassador_request_step_without_a_topic_creates_nothing(
    client, higher_ed_school, higher_ed_formation
):
    _seed_after_training(
        client,
        higher_ed_school,
        higher_ed_formation,
        current="training_ambassador_request",
        values={"wants_training_ambassador": True},
    )

    response = _post_step(client, "training_ambassador_request", {"topic": ""})

    assert b'name="action" value="training_ambassador_request"' in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_show_skip_inscription_step_modal_submits_the_skipped_ambassador_screen(client):
    response = client.get(
        reverse("show_skip_inscription_step_modal", args=["training_ambassador_request"])
    )

    assert b'name="action" value="skip"' in response.content
    assert b'name="step" value="training_ambassador_request"' in response.content
    assert b"une ambassadrice" in response.content


@pytest.mark.django_db
def test_show_skip_inscription_step_modal_rejects_a_step_that_cannot_be_skipped(client):
    response = client.get(reverse("show_skip_inscription_step_modal", args=["identity"]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_back_from_the_training_ambassador_request_skips_the_mentoring_screen(client):
    _seed_until_training(
        client,
        "higher_education",
        current="training_ambassador_request",
        values={"wants_training_ambassador": True},
    )

    response = client.post(FUNNEL_URL, {"action": "back"})

    assert b'name="action" value="training_experience"' in response.content


def _seed_until_mentoring(client, higher_ed_school, higher_ed_formation, *, age=None):
    _seed_after_training(
        client,
        higher_ed_school,
        higher_ed_formation,
        current="mentoring_signup",
        values={"wants_mentor": True},
        identity=_identity_for_age(age) if age else {},
    )


@pytest.mark.django_db
def test_mentoring_signup_step_persists_legal_representative_email_for_a_minor(
    client, higher_ed_school, higher_ed_formation
):
    _seed_until_mentoring(client, higher_ed_school, higher_ed_formation, age=16)

    response = _post_step(
        client,
        "mentoring_signup",
        {
            "legal_representative_name": "Parent Test",
            "legal_representative_email": "parent@example.com",
            "phone": "0612345678",
        },
    )

    assert b"Saisis le code" in response.content
    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.legal_representative_name == "Parent Test"
    assert beneficiary.legal_representative_email == "parent@example.com"


@pytest.mark.django_db
def test_mentoring_signup_step_blocks_a_minor_without_legal_representative_fields(
    client, higher_ed_school, higher_ed_formation
):
    _seed_until_mentoring(client, higher_ed_school, higher_ed_formation, age=16)

    response = _post_step(client, "mentoring_signup", {"phone": "0612345678"})

    assert b"Saisis le code" not in response.content
    assert b"Ce champ est obligatoire." in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_mentoring_signup_step_creates_an_adult_beneficiary_without_legal_representative_fields(
    client, higher_ed_school, higher_ed_formation
):
    # The template never shows the legal-representative fields to an adult, so the form must
    # accept a submission carrying only the phone number.
    _seed_until_mentoring(client, higher_ed_school, higher_ed_formation)
    instance = MagicMock(success=True, failure=False, errors=[])
    with patch(
        "techpourtoutes.services.beneficiary.sign_up_for_mentoring.CreateMentoree",
        return_value=instance,
    ):
        response = _post_step(client, "mentoring_signup", {"phone": "0612345678"})

    assert b"Saisis le code" in response.content
    beneficiary = Beneficiary.objects.get(email="oceane@example.com")
    assert beneficiary.legal_representative_name == ""
    assert beneficiary.legal_representative_email == ""


@pytest.mark.django_db
def test_a_mentoring_sign_up_jobirl_refuses_sends_her_back_with_no_account(
    client, higher_ed_school, higher_ed_formation
):
    _seed_until_mentoring(client, higher_ed_school, higher_ed_formation)
    refused = MagicMock(
        success=False,
        failure=True,
        errors=["EMAIL ALREADY EXISTS"],
        failed_with_transient_error=False,
        error_kind=ErrorKind.PERMANENT,
    )
    with patch(
        "techpourtoutes.services.beneficiary.sign_up_for_mentoring.CreateMentoree",
        return_value=refused,
    ):
        response = _post_step(client, "mentoring_signup", {"phone": "0612345678"})

    assert b"Saisis le code" not in response.content
    assert "EMAIL ALREADY EXISTS" in response.content.decode()
    # She can try again: what she typed is kept, the last screen included.
    assert _funnel(client).answers["phone"] == "0612345678"
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_funnel_redirects_authenticated_user_to_account(client):
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
def test_code_step_with_valid_code_logs_in_and_redirects(client):
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


@pytest.fixture
def approved_salon(pro):
    from techpourtoutes.models import Event
    from techpourtoutes.tests.models.test_event import build_event

    salon = build_event(pro, status=Event.Status.APPROVED)
    salon.save()
    return salon


@pytest.mark.django_db
def test_inscription_funnel_carries_the_bookmarked_event_through_every_step(
    client, approved_salon
):
    client.get(NEW_FUNNEL_URL, {"saved_event": str(approved_salon.pk)})

    assert _funnel(client).answers["saved_event"] == str(approved_salon.pk)


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_account_creation_step_carries_the_bookmarked_event_onto_the_code_screen(
    client, higher_ed_school, higher_ed_formation, approved_salon
):
    # The funnel is cleared as soon as the account exists, before the code is even submitted, so
    # the event bookmark must travel as a field of the "code" screen itself.
    _seed_until_training(
        client, "higher_education", values={"saved_event": str(approved_salon.pk)}
    )

    response = _post_step(
        client,
        "training_experience",
        _higher_education_training(higher_ed_school, higher_ed_formation),
    )

    assert f'name="saved_event" value="{approved_salon.pk}"'.encode() in response.content


@pytest.mark.django_db
def test_code_step_saves_the_event_bookmarked_before_the_signup(client, approved_salon):
    beneficiary = Beneficiary.objects.create(
        username="oceane@example.com",
        email="oceane@example.com",
        first_name="Océane",
        last_name="Durand",
    )
    code = beneficiary.issue_login_code()

    client.post(
        FUNNEL_URL,
        {
            "action": "code",
            "email": beneficiary.email,
            "code": code,
            "saved_event": str(approved_salon.pk),
        },
    )

    assert list(beneficiary.saved_events.all()) == [approved_salon]


@pytest.mark.django_db
def test_code_step_lands_on_her_saved_events_when_an_event_was_bookmarked(client, approved_salon):
    beneficiary = Beneficiary.objects.create(
        username="oceane@example.com",
        email="oceane@example.com",
        first_name="Océane",
        last_name="Durand",
    )
    code = beneficiary.issue_login_code()

    response = client.post(
        FUNNEL_URL,
        {
            "action": "code",
            "email": beneficiary.email,
            "code": code,
            "saved_event": str(approved_salon.pk),
        },
    )

    assert response["HX-Redirect"] == reverse("index_beneficiary_events")


@pytest.mark.django_db
def test_code_step_welcomes_her_to_the_club_once_on_her_account(client):
    beneficiary = Beneficiary.objects.create(
        username="oceane@example.com",
        email="oceane@example.com",
        first_name="Océane",
        last_name="Durand",
    )
    code = beneficiary.issue_login_code()

    client.post(FUNNEL_URL, {"action": "code", "email": beneficiary.email, "code": code})

    assert "Bienvenue au club" in client.get(reverse("show_account")).content.decode()
    assert "Bienvenue au club" not in client.get(reverse("show_account")).content.decode()


@pytest.mark.django_db
def test_code_step_welcomes_her_to_the_club_on_her_saved_events(client, approved_salon):
    beneficiary = Beneficiary.objects.create(
        username="oceane@example.com",
        email="oceane@example.com",
        first_name="Océane",
        last_name="Durand",
    )
    code = beneficiary.issue_login_code()

    client.post(
        FUNNEL_URL,
        {
            "action": "code",
            "email": beneficiary.email,
            "code": code,
            "saved_event": str(approved_salon.pk),
        },
    )

    content = client.get(reverse("index_beneficiary_events")).content.decode()
    assert "Bienvenue au club" in content


@pytest.mark.django_db
def test_email_step_hands_the_bookmarked_event_over_when_the_account_already_exists(
    client, approved_salon, beneficiary
):
    client.get(NEW_FUNNEL_URL, {"saved_event": str(approved_salon.pk)})

    response = _post_step(client, "email", {"email": beneficiary.email})

    assert f"saved_event={approved_salon.pk}" in response["HX-Redirect"]


@pytest.mark.django_db
def test_code_step_with_invalid_code_shows_error(client):
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
def test_resend_step_mails_a_new_code_and_stays_on_the_code_screen(client):
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
def test_resend_step_with_unknown_email_sends_nothing(client):
    response = client.post(FUNNEL_URL, {"action": "resend", "email": "inconnue@example.com"})

    assert response.status_code == 200
    assert b"Saisis le code" in response.content
    assert mail.outbox == []


# The answers were valid when given, but no longer are by the time the account is created.
@pytest.mark.django_db
def test_an_email_taken_meanwhile_sends_her_to_the_login_instead_of_creating(
    client, higher_ed_school, higher_ed_formation
):
    _seed_until_training(client, "higher_education")
    User.objects.create_user(
        username="oceane@example.com",
        email="oceane@example.com",
        password="irrelevant",
        first_name="Océane",
        last_name="Autre",
    )

    response = _post_step(
        client,
        "training_experience",
        _higher_education_training(higher_ed_school, higher_ed_formation),
    )

    assert "se-connecter" in response["HX-Redirect"]
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_a_school_removed_meanwhile_sends_her_back_to_the_training_screen(
    client, higher_ed_school, higher_ed_formation
):
    _seed_after_training(
        client,
        higher_ed_school,
        higher_ed_formation,
        current="training_ambassador_request",
        values={"wants_training_ambassador": True},
    )
    higher_ed_school.delete()

    response = _post_step(client, "training_ambassador_request", {"topic": "Parcoursup"})

    assert b'name="action" value="training_experience"' in response.content
    assert "Sélectionnez un établissement valide.".encode() in response.content
    assert not Beneficiary.objects.exists()


@pytest.mark.django_db
def test_progress_ignores_the_mentoring_screen_when_it_is_not_part_of_the_funnel(client):
    _seed_funnel(client, current="study_status", email=_EMAIL, identity=_IDENTITY)

    response = _post_step(client, "study_status", {"study_status": "higher_education"})

    # Three counted steps — the email screen takes no share — plus the final segment reserved
    # for the success screen.
    assert b"width: 75%" in response.content


@pytest.mark.django_db
def test_progress_counts_the_mentoring_screen_when_a_mentor_is_wanted(client):
    client.get(f"{NEW_FUNNEL_URL}?wants_mentor=1")
    _post_step(client, "email", _EMAIL)
    _post_step(client, "identity", _IDENTITY)

    response = _post_step(client, "study_status", {"study_status": "higher_education"})

    assert b"width: 60%" in response.content


@pytest.mark.django_db
def test_back_step_returns_previous_step_prefilled(client):
    _seed_funnel(client, current="study_status", email=_EMAIL, identity=_identity_for_age(20))

    response = client.post(FUNNEL_URL, {"action": "back"})

    assert b'name="action" value="identity"' in response.content
    assert "Océane".encode() in response.content
    assert f'value="{_birth_date_for_age(20).isoformat()}"'.encode() in response.content
