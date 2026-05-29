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


@pytest.mark.django_db
@override_settings(BREVO_PRO_LIST_ID=42, BREVO_API_KEY="test")
def test_upsert_brevo_contact_calls_client_upsert(pro, mock_brevo_client):
    result = UpsertBrevoContact(instance=pro)

    assert result.success
    mock_brevo_client.upsert_contact.assert_called_once()
    call_kwargs = mock_brevo_client.upsert_contact.call_args.kwargs
    assert call_kwargs["ext_id"] == str(pro.pk)
    assert call_kwargs["list_id"] == 42
    assert call_kwargs["attributes"]["EMAIL"] == "alice@example.com"


@pytest.mark.django_db
@override_settings(BREVO_API_KEY="test")
def test_upsert_brevo_contact_skips_when_no_mapping(db, mock_brevo_client):
    from techpourtoutes.models import User

    user = User.objects.create_user(username="bare@x.fr", email="bare@x.fr")

    result = UpsertBrevoContact(instance=user)

    assert result.success
    mock_brevo_client.upsert_contact.assert_not_called()


@pytest.mark.django_db
@override_settings(BREVO_PRO_LIST_ID=42, BREVO_API_KEY="test")
def test_upsert_brevo_contact_captures_api_error(pro, mock_brevo_client):
    mock_brevo_client.upsert_contact.side_effect = ApiError(
        status_code=400, body={"message": "bad"}
    )

    result = UpsertBrevoContact(instance=pro)

    assert result.failure
    assert result.errors


@pytest.mark.django_db
@override_settings(BREVO_PRO_LIST_ID=42, BREVO_API_KEY="test")
@pytest.mark.parametrize(
    "status_code,is_transient",
    [(400, False), (404, False), (422, False), (429, True), (500, True), (503, True)],
)
def test_is_transient_failure_classifies_by_status_code(
    pro, mock_brevo_client, status_code, is_transient
):
    mock_brevo_client.upsert_contact.side_effect = ApiError(
        status_code=status_code, body={"message": "x"}
    )

    result = UpsertBrevoContact(instance=pro)

    assert result.is_transient_failure is is_transient


@pytest.mark.django_db
@override_settings(BREVO_PRO_LIST_ID=42, BREVO_API_KEY="test")
def test_is_transient_failure_false_on_success(pro, mock_brevo_client):
    result = UpsertBrevoContact(instance=pro)

    assert result.success
    assert result.is_transient_failure is False


@pytest.mark.django_db
@override_settings(BREVO_API_KEY="test")
def test_delete_brevo_contact_removes_from_list_when_contact_in_multiple_lists(
    mock_brevo_client,
):
    mock_brevo_client.get_contact.return_value = SimpleNamespace(list_ids=[42, 99])

    result = DeleteBrevoContact(ext_id="abc-123", list_id=42)

    assert result.success
    mock_brevo_client.get_contact.assert_called_once_with(ext_id="abc-123")
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
    mock_brevo_client.get_contact.assert_called_once_with(ext_id="abc-123")
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
