from unittest.mock import patch

import pytest
from brevo.core.api_error import ApiError
from django.test import override_settings

from techpourtoutes.services.upsert_manifeste_signatory import UpsertManifesteSignatory


def _signatory_kwargs(**overrides):
    return {
        "first_name": "Manon",
        "last_name": "Desbordes",
        "email": "manon@example.com",
        "structure_name": "Latitudes",
        **overrides,
    }


@pytest.fixture
def mock_brevo_client():
    with patch("techpourtoutes.services.brevo_api.base_service.BrevoClient") as mock:
        yield mock.return_value


@override_settings(BREVO_MANIFESTE_LIST_ID=99, BREVO_API_KEY="test")
def test_upsert_manifeste_signatory_fetches_contact_by_email(mock_brevo_client):
    UpsertManifesteSignatory(**_signatory_kwargs())

    mock_brevo_client.get_contact.assert_called_once_with(
        identifier="manon@example.com", identifier_type="email_id"
    )


@override_settings(BREVO_MANIFESTE_LIST_ID=99, BREVO_API_KEY="test")
def test_upsert_manifeste_signatory_updates_when_contact_exists(mock_brevo_client):
    result = UpsertManifesteSignatory(**_signatory_kwargs())

    assert result.success
    mock_brevo_client.update_contact.assert_called_once()
    call_kwargs = mock_brevo_client.update_contact.call_args.kwargs
    assert call_kwargs["identifier"] == "manon@example.com"
    assert call_kwargs["identifier_type"] == "email_id"
    assert call_kwargs["list_id"] == 99
    assert call_kwargs["attributes"]["PRENOM"] == "Manon"
    assert call_kwargs["attributes"]["NOM_DE_LA_STRUCTURE"] == "Latitudes"
    mock_brevo_client.upsert_contact.assert_not_called()


@override_settings(BREVO_MANIFESTE_LIST_ID=99, BREVO_API_KEY="test")
def test_upsert_manifeste_signatory_creates_when_contact_not_found(mock_brevo_client):
    mock_brevo_client.get_contact.side_effect = ApiError(
        status_code=404, body={"message": "Contact not found"}
    )

    result = UpsertManifesteSignatory(**_signatory_kwargs())

    assert result.success
    mock_brevo_client.upsert_contact.assert_called_once()
    call_kwargs = mock_brevo_client.upsert_contact.call_args.kwargs
    assert call_kwargs.get("ext_id") is None
    assert call_kwargs["list_id"] == 99
    assert call_kwargs["attributes"]["EMAIL"] == "manon@example.com"
    mock_brevo_client.update_contact.assert_not_called()


@override_settings(BREVO_MANIFESTE_LIST_ID=0, BREVO_API_KEY="test")
def test_upsert_manifeste_signatory_skips_without_list(mock_brevo_client):
    result = UpsertManifesteSignatory(**_signatory_kwargs())

    assert result.success
    mock_brevo_client.get_contact.assert_not_called()


@override_settings(BREVO_MANIFESTE_LIST_ID=99, BREVO_API_KEY="test")
def test_upsert_manifeste_signatory_captures_update_error(mock_brevo_client):
    mock_brevo_client.update_contact.side_effect = ApiError(
        status_code=400, body={"message": "bad"}
    )

    result = UpsertManifesteSignatory(**_signatory_kwargs())

    assert result.failure
    assert result.errors


@override_settings(BREVO_MANIFESTE_LIST_ID=99, BREVO_API_KEY="test")
def test_upsert_manifeste_signatory_fails_on_get_contact_error(mock_brevo_client):
    mock_brevo_client.get_contact.side_effect = ApiError(
        status_code=500, body={"message": "server error"}
    )

    result = UpsertManifesteSignatory(**_signatory_kwargs())

    assert result.failure
    assert result.errors
    mock_brevo_client.update_contact.assert_not_called()
    mock_brevo_client.upsert_contact.assert_not_called()
