from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

CHANGELIST = "admin:techpourtoutes_beneficiary_changelist"


def _validate_url(beneficiary):
    return reverse("admin:beneficiary_validate_mentoring", args=[beneficiary.pk])


def _change_url(beneficiary):
    return reverse("admin:techpourtoutes_beneficiary_change", args=[beneficiary.pk])


def _change_form_data(client, beneficiary, **overrides):
    """Everything the change form posts back, so a decision travels with real field values."""
    form = client.get(_change_url(beneficiary)).context["adminform"].form
    return {
        **{name: form[name].value() or "" for name in form.fields},
        "training_experiences-TOTAL_FORMS": "0",
        "training_experiences-INITIAL_FORMS": "0",
        "saves-TOTAL_FORMS": "0",
        "saves-INITIAL_FORMS": "0",
        **overrides,
    }


@pytest.mark.django_db
def test_changelist_action_only_shown_when_pending_validation(
    verified_admin_client, beneficiaries_by_mentoring_status
):
    content = verified_admin_client.get(reverse(CHANGELIST)).content.decode()

    assert _validate_url(beneficiaries_by_mentoring_status["pending"]) in content
    assert _validate_url(beneficiaries_by_mentoring_status["not_concerned"]) not in content
    assert _validate_url(beneficiaries_by_mentoring_status["registered"]) not in content


@pytest.mark.django_db
def test_validate_mentoring_registers_beneficiary_and_redirects(
    verified_admin_client, beneficiaries_by_mentoring_status
):
    beneficiary = beneficiaries_by_mentoring_status["pending"]
    instance = MagicMock(success=True, failure=False, errors=[])
    with patch(
        "techpourtoutes.admin.models.beneficiary.CreateMentoree", return_value=instance
    ) as mock:
        response = verified_admin_client.post(_validate_url(beneficiary))

    mock.assert_called_once_with(beneficiary=beneficiary)
    assert response.status_code == 302
    assert response["Location"] == reverse(CHANGELIST)


@pytest.mark.django_db
def test_validate_mentoring_shows_errors_on_failure(
    verified_admin_client, beneficiaries_by_mentoring_status
):
    instance = MagicMock(success=False, failure=True, errors=["Jobirl est indisponible."])
    with patch("techpourtoutes.admin.models.beneficiary.CreateMentoree", return_value=instance):
        response = verified_admin_client.post(
            _validate_url(beneficiaries_by_mentoring_status["pending"]), follow=True
        )

    assert "Jobirl est indisponible." in response.content.decode()


@pytest.mark.django_db
def test_validate_mentoring_button_shown_on_change_form_only_while_pending(
    verified_admin_client, beneficiaries_by_mentoring_status
):
    content = verified_admin_client.get(
        _change_url(beneficiaries_by_mentoring_status["pending"])
    ).content.decode()
    assert 'name="_validate_mentoring"' in content

    content = verified_admin_client.get(
        _change_url(beneficiaries_by_mentoring_status["not_concerned"])
    ).content.decode()
    assert 'name="_validate_mentoring"' not in content

    content = verified_admin_client.get(
        _change_url(beneficiaries_by_mentoring_status["registered"])
    ).content.decode()
    assert 'name="_validate_mentoring"' not in content


@pytest.mark.django_db
def test_validating_mentoring_from_the_change_form_saves_the_edits_it_travels_with(
    verified_admin_client, beneficiaries_by_mentoring_status
):
    """The legal rep details a Pro just corrected are what has to reach Jobirl."""
    beneficiary = beneficiaries_by_mentoring_status["pending"]
    instance = MagicMock(success=True, failure=False, errors=[])
    data = _change_form_data(
        verified_admin_client,
        beneficiary,
        legal_representative_name="Nouveau Nom",
        _validate_mentoring="",
    )

    with patch(
        "techpourtoutes.admin.models.beneficiary.CreateMentoree", return_value=instance
    ) as mock:
        response = verified_admin_client.post(_change_url(beneficiary), data)

    assert response.status_code == 302
    beneficiary.refresh_from_db()
    assert beneficiary.legal_representative_name == "Nouveau Nom"
    mock.assert_called_once()
    assert mock.call_args.kwargs["beneficiary"].legal_representative_name == "Nouveau Nom"


@pytest.mark.django_db
def test_validating_mentoring_from_the_change_form_shows_errors_on_failure(
    verified_admin_client, beneficiaries_by_mentoring_status
):
    beneficiary = beneficiaries_by_mentoring_status["pending"]
    instance = MagicMock(success=False, failure=True, errors=["Jobirl est indisponible."])
    data = _change_form_data(verified_admin_client, beneficiary, _validate_mentoring="")

    with patch("techpourtoutes.admin.models.beneficiary.CreateMentoree", return_value=instance):
        response = verified_admin_client.post(_change_url(beneficiary), data, follow=True)

    assert "Jobirl est indisponible." in response.content.decode()


@pytest.mark.django_db
def test_a_plain_save_does_not_contact_jobirl(
    verified_admin_client, beneficiaries_by_mentoring_status
):
    beneficiary = beneficiaries_by_mentoring_status["pending"]
    data = _change_form_data(verified_admin_client, beneficiary, first_name="Elise Modifiée")

    with patch("techpourtoutes.admin.models.beneficiary.CreateMentoree") as mock:
        response = verified_admin_client.post(_change_url(beneficiary), data)

    assert response.status_code == 302
    beneficiary.refresh_from_db()
    assert beneficiary.first_name == "Elise Modifiée"
    mock.assert_not_called()


@pytest.mark.django_db
def test_legal_rep_fields_lock_once_registered_on_jobirl(
    verified_admin_client, beneficiaries_by_mentoring_status
):
    content = verified_admin_client.get(
        _change_url(beneficiaries_by_mentoring_status["pending"])
    ).content.decode()
    assert 'name="legal_representative_name"' in content

    content = verified_admin_client.get(
        _change_url(beneficiaries_by_mentoring_status["registered"])
    ).content.decode()
    assert 'name="legal_representative_name"' not in content
    assert 'name="legal_representative_email"' not in content


@pytest.mark.django_db
def test_an_attempt_to_edit_the_locked_legal_rep_fields_is_ignored(
    verified_admin_client, beneficiaries_by_mentoring_status
):
    beneficiary = beneficiaries_by_mentoring_status["registered"]
    data = _change_form_data(
        verified_admin_client, beneficiary, legal_representative_name="Nom modifié"
    )

    response = verified_admin_client.post(_change_url(beneficiary), data)

    assert response.status_code == 302
    beneficiary.refresh_from_db()
    assert beneficiary.legal_representative_name != "Nom modifié"


@pytest.mark.django_db
def test_beneficiary_page_lists_training_experiences(
    verified_admin_client, beneficiary, beneficiary_experience
):
    url = reverse("admin:techpourtoutes_beneficiary_change", args=[beneficiary.pk])
    content = verified_admin_client.get(url).content.decode()
    assert "Spécialité mathématiques" in content
    assert "Lycée Voltaire" in content


@pytest.mark.django_db
def test_beneficiary_page_lists_the_events_she_saved(verified_admin_client, beneficiary, event):
    from techpourtoutes.models import SavedEvent

    SavedEvent.objects.toggle(event=event, beneficiary=beneficiary)

    url = reverse("admin:techpourtoutes_beneficiary_change", args=[beneficiary.pk])
    content = verified_admin_client.get(url).content.decode()

    assert "Salon des métiers du numérique" in content
    assert "Événements sauvegardés" in content
