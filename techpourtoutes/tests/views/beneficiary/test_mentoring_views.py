from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

from techpourtoutes.models import Level
from techpourtoutes.utils.dates import adult_birth_date

ADD_MENTORING_URL = "/devenir-mentoree/"


def _birth_date_for_age(age):
    today = date.today()
    try:
        return today.replace(year=today.year - age)
    except ValueError:  # 29 February
        return today.replace(year=today.year - age, day=28)


@pytest.mark.django_db
def test_add_mentoring_requires_login(client):
    response = client.get(ADD_MENTORING_URL)

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]


@pytest.mark.django_db
def test_add_mentoring_redirects_non_beneficiary_with_error(client, pro):
    client.force_login(pro)

    response = client.get(ADD_MENTORING_URL, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1][0] == reverse("account")
    messages_list = [str(m) for m in response.context["messages"]]
    assert any("réservée aux bénéficiaires" in m for m in messages_list)


@pytest.mark.django_db
def test_add_mentoring_redirects_when_already_registered(client, beneficiary):
    beneficiary.jobirl_user_id = 42
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.get(ADD_MENTORING_URL, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1][0] == reverse("account")


@pytest.mark.django_db
def test_add_mentoring_get_renders_form_for_adult(client, beneficiary, beneficiary_experience):
    client.force_login(beneficiary)

    response = client.get(ADD_MENTORING_URL)

    assert response.status_code == 200
    assert response.context["is_minor"] is False
    assert "responsable légale" not in response.content.decode()


@pytest.mark.django_db
def test_add_mentoring_get_renders_form_for_minor(client, beneficiary, beneficiary_experience):
    beneficiary.birth_date = _birth_date_for_age(16)
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.get(ADD_MENTORING_URL)

    assert response.status_code == 200
    assert response.context["is_minor"] is True
    assert "responsable légale" in response.content.decode()


@pytest.mark.django_db
def test_add_mentoring_post_valid_adult_signs_up_and_redirects(
    client, beneficiary, beneficiary_experience
):
    client.force_login(beneficiary)
    instance = MagicMock(success=True, failure=False, errors=[])

    with patch(
        "techpourtoutes.services.beneficiary.sign_up_for_mentoring.CreateMentoree",
        return_value=instance,
    ):
        response = client.post(
            ADD_MENTORING_URL, {"action": "mentoring_signup", "phone": "0612345678"}
        )

    assert response["HX-Redirect"] == reverse("account")
    beneficiary.refresh_from_db()
    assert beneficiary.phone == "+33612345678"


@pytest.mark.django_db
def test_add_mentoring_post_missing_legal_representative_fields_for_minor(
    client, beneficiary, beneficiary_experience
):
    beneficiary.birth_date = _birth_date_for_age(16)
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.post(
        ADD_MENTORING_URL, {"action": "mentoring_signup", "phone": "0612345678"}
    )

    assert response.status_code == 200
    assert "Ce champ est obligatoire." in response.content.decode()
    beneficiary.refresh_from_db()
    assert beneficiary.legal_representative_name == ""


@pytest.mark.django_db
def test_add_mentoring_get_asks_for_the_birth_date_when_the_account_has_none(
    client, beneficiary, beneficiary_experience
):
    beneficiary.birth_date = None
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.get(ADD_MENTORING_URL)

    assert response.status_code == 200
    assert response.context["needs_birth_date"] is True
    assert response.context["is_minor"] is False
    assert 'name="birth_date"' in response.content.decode()


@pytest.mark.django_db
def test_add_mentoring_ships_the_legal_representative_fields_for_alpine_to_reveal(
    client, beneficiary, beneficiary_experience
):
    beneficiary.birth_date = None
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.get(ADD_MENTORING_URL)
    content = response.content.decode()

    # Minority is only settled once she picks a date, so the fields ship hidden and Alpine
    # reveals them right away rather than after a rejected submit.
    assert response.context["adult_birth_date"] == adult_birth_date().isoformat()
    assert 'name="legal_representative_email"' in content
    assert 'x-show="isMinor"' in content


@pytest.mark.django_db
def test_add_mentoring_post_saves_the_submitted_birth_date_of_an_adult(
    client, beneficiary, beneficiary_experience
):
    beneficiary.birth_date = None
    beneficiary.save()
    client.force_login(beneficiary)
    birth_date = _birth_date_for_age(20)

    with patch(
        "techpourtoutes.services.beneficiary.sign_up_for_mentoring.CreateMentoree",
        return_value=MagicMock(success=True, failure=False, errors=[]),
    ):
        response = client.post(
            ADD_MENTORING_URL,
            {
                "action": "mentoring_signup",
                "phone": "0612345678",
                "birth_date": birth_date.isoformat(),
            },
        )

    assert response["HX-Redirect"] == reverse("account")
    beneficiary.refresh_from_db()
    assert beneficiary.birth_date == birth_date


@pytest.mark.django_db
def test_add_mentoring_post_without_a_birth_date_when_the_account_has_none(
    client, beneficiary, beneficiary_experience
):
    beneficiary.birth_date = None
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.post(
        ADD_MENTORING_URL, {"action": "mentoring_signup", "phone": "0612345678"}
    )

    assert response.status_code == 200
    assert response.context["form"].errors["birth_date"]
    beneficiary.refresh_from_db()
    assert beneficiary.birth_date is None


@pytest.mark.django_db
def test_add_mentoring_post_with_a_minor_birth_date_requires_a_legal_representative(
    client, beneficiary, beneficiary_experience
):
    beneficiary.birth_date = None
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.post(
        ADD_MENTORING_URL,
        {
            "action": "mentoring_signup",
            "phone": "0612345678",
            "birth_date": _birth_date_for_age(16).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.context["is_minor"] is True
    assert "Ce champ est obligatoire." in response.content.decode()
    beneficiary.refresh_from_db()
    assert beneficiary.legal_representative_name == ""


@pytest.mark.django_db
def test_add_mentoring_post_service_failure_shows_error(
    client, beneficiary, beneficiary_experience
):
    client.force_login(beneficiary)
    refused = MagicMock(
        success=False,
        failure=True,
        errors=["EMAIL ALREADY EXISTS"],
        failed_with_transient_error=False,
    )

    with patch(
        "techpourtoutes.services.beneficiary.sign_up_for_mentoring.CreateMentoree",
        return_value=refused,
    ):
        response = client.post(
            ADD_MENTORING_URL, {"action": "mentoring_signup", "phone": "0612345678"}
        )

    assert response.status_code == 200
    assert "EMAIL ALREADY EXISTS" in response.content.decode()
    beneficiary.refresh_from_db()
    assert beneficiary.jobirl_user_id is None


def _parcours_post(school, formation):
    return {
        "action": "training_experience",
        "study_status": "high_school",
        "level": "terminale",
        "school_id": str(school.pk),
        "school_label": school.location_label,
        "formation_id": str(formation.pk),
        "formation_label": formation.name,
    }


@pytest.mark.django_db
def test_add_mentoring_starts_on_the_study_status_when_the_account_has_no_parcours(
    client, beneficiary
):
    client.force_login(beneficiary)

    response = client.get(ADD_MENTORING_URL)

    assert response.context["step"] == "study_status"
    assert "Où en es-tu dans tes études ?" in response.content.decode()


@pytest.mark.django_db
def test_add_mentoring_starts_on_the_signup_when_the_account_has_a_parcours(
    client, beneficiary, beneficiary_experience
):
    client.force_login(beneficiary)

    response = client.get(ADD_MENTORING_URL)

    assert response.context["step"] == "mentoring_signup"
    assert "Où en es-tu dans tes études ?" not in response.content.decode()


@pytest.mark.django_db
def test_add_mentoring_study_status_step_advances_to_the_parcours(client, beneficiary):
    client.force_login(beneficiary)

    response = client.post(
        ADD_MENTORING_URL, {"action": "study_status", "study_status": "high_school"}
    )

    assert response.context["step"] == "training_experience"
    assert "En quelle classe es-tu ?*" in response.content.decode()


@pytest.mark.django_db
def test_add_mentoring_study_status_step_without_an_answer_stays_put(client, beneficiary):
    client.force_login(beneficiary)

    response = client.post(ADD_MENTORING_URL, {"action": "study_status"})

    assert response.context["step"] == "study_status"
    assert response.context["form"].errors["study_status"]


@pytest.mark.django_db
def test_add_mentoring_parcours_step_with_an_incomplete_answer_stays_put(
    client, beneficiary, school, formation
):
    client.force_login(beneficiary)
    payload = _parcours_post(school, formation)
    del payload["school_id"]
    del payload["school_label"]

    response = client.post(ADD_MENTORING_URL, payload)

    assert response.context["step"] == "training_experience"
    assert response.context["form"].errors
    assert not beneficiary.training_experiences.exists()


@pytest.mark.django_db
def test_add_mentoring_parcours_step_saves_it_and_advances_to_the_signup(
    client, beneficiary, school, formation
):
    client.force_login(beneficiary)

    response = client.post(ADD_MENTORING_URL, _parcours_post(school, formation))

    assert response.context["step"] == "mentoring_signup"
    experience = beneficiary.training_experiences.get()
    assert experience.school == school
    assert experience.formation == formation
    assert experience.level == Level.TERMINALE


@pytest.mark.django_db
def test_add_mentoring_parcours_step_with_a_forged_study_status_returns_to_the_question(
    client, beneficiary, school, formation
):
    client.force_login(beneficiary)

    response = client.post(
        ADD_MENTORING_URL, {**_parcours_post(school, formation), "study_status": "whatever"}
    )

    assert response.context["step"] == "study_status"
    assert not beneficiary.training_experiences.exists()
