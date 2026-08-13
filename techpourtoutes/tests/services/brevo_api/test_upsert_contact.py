import pytest
from brevo.core.api_error import ApiError
from django.test import override_settings

from techpourtoutes.services.brevo_api.upsert_contact import UpsertBrevoContact


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
