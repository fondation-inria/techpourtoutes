from unittest.mock import patch

import pytest
from brevo.core.api_error import ApiError
from django.test import override_settings

from techpourtoutes.services.sync_brevo_contact import SyncBrevoContact


@pytest.fixture
def mock_brevo_client():
    with patch("techpourtoutes.services.brevo_api.base_service.BrevoClient") as mock:
        yield mock.return_value


@pytest.mark.django_db
@override_settings(BREVO_PRO_LIST_ID=42, BREVO_API_KEY="test")
def test_sync_brevo_contact_calls_client_upsert(pro, mock_brevo_client):
    result = SyncBrevoContact(instance=pro)

    assert result.success
    mock_brevo_client.upsert_contact.assert_called_once()
    call_kwargs = mock_brevo_client.upsert_contact.call_args.kwargs
    assert call_kwargs["ext_id"] == str(pro.pk)
    assert call_kwargs["list_id"] == 42
    assert call_kwargs["attributes"]["EMAIL"] == "alice@example.com"


@pytest.mark.django_db
@override_settings(BREVO_API_KEY="test")
def test_sync_brevo_contact_skips_when_no_mapping(db, mock_brevo_client):
    from techpourtoutes.models import User

    user = User.objects.create_user(username="bare@x.fr", email="bare@x.fr")

    result = SyncBrevoContact(instance=user)

    assert result.success
    mock_brevo_client.upsert_contact.assert_not_called()


@pytest.mark.django_db
@override_settings(BREVO_PRO_LIST_ID=42, BREVO_API_KEY="test")
@pytest.mark.parametrize(
    "message",
    [
        "Unable to create contact, SMS is already associated with another Contact",
        "Unable to update contact, SMS or EXT_ID are already associated with another Contact",
    ],
)
def test_sync_brevo_contact_retries_without_sms_on_conflict(pro, mock_brevo_client, message):
    mock_brevo_client.upsert_contact.side_effect = [
        ApiError(status_code=400, body={"message": message}),
        None,
    ]

    result = SyncBrevoContact(instance=pro)

    assert result.success
    assert mock_brevo_client.upsert_contact.call_count == 2
    second_call_attrs = mock_brevo_client.upsert_contact.call_args_list[1].kwargs["attributes"]
    assert "SMS" not in second_call_attrs


@pytest.mark.django_db
@override_settings(BREVO_PRO_LIST_ID=42, BREVO_API_KEY="test")
def test_sync_brevo_contact_fails_on_non_sms_api_error(pro, mock_brevo_client):
    mock_brevo_client.upsert_contact.side_effect = ApiError(
        status_code=500, body={"message": "server error"}
    )

    result = SyncBrevoContact(instance=pro)

    assert result.failure
    assert result.status_code == 500
