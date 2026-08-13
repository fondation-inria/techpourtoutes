from types import SimpleNamespace

import pytest
from brevo.core.api_error import ApiError
from django.test import override_settings

from techpourtoutes.services.brevo_api.delete_contact import DeleteBrevoContact


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
