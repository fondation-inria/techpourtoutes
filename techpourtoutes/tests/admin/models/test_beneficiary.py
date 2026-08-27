from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

CHANGELIST = "admin:techpourtoutes_beneficiary_changelist"


def _validate_url(beneficiary):
    return reverse("admin:beneficiary_validate_mentoring", args=[beneficiary.pk])


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
def test_beneficiary_page_lists_training_experiences(
    verified_admin_client, beneficiary, beneficiary_experience
):
    url = reverse("admin:techpourtoutes_beneficiary_change", args=[beneficiary.pk])
    content = verified_admin_client.get(url).content.decode()
    assert "Spécialité mathématiques" in content
    assert "Lycée Voltaire" in content
