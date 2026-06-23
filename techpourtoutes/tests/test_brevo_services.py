from types import SimpleNamespace
from unittest.mock import patch

import pytest
from brevo.core.api_error import ApiError
from django.test import override_settings

from techpourtoutes.services.brevo_api.delete_contact import DeleteBrevoContact
from techpourtoutes.services.brevo_api.upsert_contact import UpsertBrevoContact


@pytest.fixture
def mock_brevo_client():
    with patch("techpourtoutes.services.brevo_api.base_service.BrevoClient") as mock:
        yield mock.return_value


# ── UpsertBrevoContact ─────────────────────────────────────


@override_settings(BREVO_API_KEY="test")
def test_upsert_brevo_contact_calls_client_upsert(mock_brevo_client):
    result = UpsertBrevoContact(
        ext_id="abc-123", list_id=42, attributes={"EMAIL": "x@y.fr", "PRENOM": "X"}
    )

    assert result.success
    mock_brevo_client.upsert_contact.assert_called_once()
    call_kwargs = mock_brevo_client.upsert_contact.call_args.kwargs
    assert call_kwargs["ext_id"] == "abc-123"
    assert call_kwargs["list_id"] == 42
    assert call_kwargs["attributes"]["EMAIL"] == "x@y.fr"


@override_settings(BREVO_API_KEY="test")
def test_upsert_brevo_contact_captures_api_error(mock_brevo_client):
    mock_brevo_client.upsert_contact.side_effect = ApiError(
        status_code=400, body={"message": "bad"}
    )

    result = UpsertBrevoContact(ext_id="abc-123", list_id=42, attributes={"EMAIL": "x@y.fr"})

    assert result.failure
    assert result.errors


@override_settings(BREVO_API_KEY="test")
@pytest.mark.parametrize("status_code", [400, 404, 422, 429, 500, 503])
def test_status_code_is_set_on_api_error(mock_brevo_client, status_code):
    mock_brevo_client.upsert_contact.side_effect = ApiError(
        status_code=status_code, body={"message": "x"}
    )

    result = UpsertBrevoContact(ext_id="abc-123", list_id=42, attributes={"EMAIL": "x@y.fr"})

    assert result.status_code == status_code


@override_settings(BREVO_API_KEY="test")
@pytest.mark.parametrize(
    "message",
    [
        "Unable to create contact, SMS is already associated with another Contact",
        "Unable to update contact, SMS or EXT_ID are already associated with another Contact",
    ],
)
def test_upsert_brevo_contact_errors_contain_sms_conflict_detail(mock_brevo_client, message):
    mock_brevo_client.upsert_contact.side_effect = ApiError(
        status_code=400, body={"message": message}
    )

    result = UpsertBrevoContact(ext_id="abc-123", list_id=42, attributes={"EMAIL": "x@y.fr"})

    assert result.failure
    assert "SMS" in result.errors[0] and "already associated" in result.errors[0]


# ── DeleteBrevoContact ────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(BREVO_API_KEY="test")
def test_delete_brevo_contact_removes_from_list_when_contact_in_multiple_lists(
    mock_brevo_client,
):
    mock_brevo_client.get_contact.return_value = SimpleNamespace(list_ids=[42, 99])

    result = DeleteBrevoContact(ext_id="abc-123", list_id=42)

    assert result.success
    mock_brevo_client.get_contact.assert_called_once_with(identifier="abc-123")
    mock_brevo_client.remove_contact_from_list.assert_called_once_with(
        ext_id="abc-123", list_id=42
    )
    mock_brevo_client.delete_contact.assert_not_called()


@pytest.mark.django_db
@override_settings(BREVO_API_KEY="test")
def test_delete_brevo_contact_deletes_when_contact_in_single_list(mock_brevo_client):
    mock_brevo_client.get_contact.return_value = SimpleNamespace(list_ids=[42])

    result = DeleteBrevoContact(ext_id="abc-123", list_id=42)

    assert result.success
    mock_brevo_client.get_contact.assert_called_once_with(identifier="abc-123")
    mock_brevo_client.delete_contact.assert_called_once_with(ext_id="abc-123")
    mock_brevo_client.remove_contact_from_list.assert_not_called()


@pytest.mark.django_db
@override_settings(BREVO_API_KEY="test")
def test_delete_brevo_contact_captures_get_contact_error(mock_brevo_client):
    mock_brevo_client.get_contact.side_effect = ApiError(status_code=404, body={"message": "gone"})

    result = DeleteBrevoContact(ext_id="abc-123", list_id=42)

    assert result.failure
    assert result.errors
    mock_brevo_client.delete_contact.assert_not_called()
    mock_brevo_client.remove_contact_from_list.assert_not_called()
