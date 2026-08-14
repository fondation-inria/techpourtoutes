from unittest.mock import patch

import pytest
from django.test import override_settings

from techpourtoutes.clients.brevo import BrevoClient


@pytest.fixture
def mock_brevo_sdk():
    with patch("techpourtoutes.clients.brevo.Brevo") as mock:
        yield mock


@override_settings(BREVO_API_KEY="test-key")
def test_brevo_client_init_passes_api_key(mock_brevo_sdk):
    BrevoClient()

    mock_brevo_sdk.assert_called_once_with(api_key="test-key")


@override_settings(BREVO_API_KEY="test-key")
def test_upsert_contact_calls_create_contact_with_update_enabled(mock_brevo_sdk):
    sdk_instance = mock_brevo_sdk.return_value

    BrevoClient().upsert_contact(
        ext_id="abc-123",
        list_id=42,
        attributes={"EMAIL": "x@y.fr", "PRENOM": "X"},
    )

    sdk_instance.contacts.create_contact.assert_called_once_with(
        email="x@y.fr",
        ext_id="abc-123",
        list_ids=[42],
        update_enabled=True,
        attributes={"PRENOM": "X"},
    )


@override_settings(BREVO_API_KEY="test-key")
def test_upsert_contact_omits_ext_id_when_not_provided(mock_brevo_sdk):
    sdk_instance = mock_brevo_sdk.return_value

    BrevoClient().upsert_contact(
        list_id=42,
        attributes={"EMAIL": "x@y.fr", "PRENOM": "X"},
    )

    call_kwargs = sdk_instance.contacts.create_contact.call_args.kwargs
    assert "ext_id" not in call_kwargs


@override_settings(BREVO_API_KEY="test-key")
def test_delete_contact_calls_sdk_with_ext_id_identifier(mock_brevo_sdk):
    sdk_instance = mock_brevo_sdk.return_value

    BrevoClient().delete_contact(ext_id="abc-123")

    sdk_instance.contacts.delete_contact.assert_called_once_with(
        "abc-123", identifier_type="ext_id"
    )


@override_settings(BREVO_API_KEY="test-key")
def test_get_contact_defaults_to_ext_id_identifier(mock_brevo_sdk):
    sdk_instance = mock_brevo_sdk.return_value

    BrevoClient().get_contact(identifier="abc-123")

    sdk_instance.contacts.get_contact_info.assert_called_once_with(
        "abc-123", identifier_type="ext_id"
    )


@override_settings(BREVO_API_KEY="test-key")
def test_get_contact_supports_email_id_identifier(mock_brevo_sdk):
    sdk_instance = mock_brevo_sdk.return_value

    BrevoClient().get_contact(identifier="x@y.fr", identifier_type="email_id")

    sdk_instance.contacts.get_contact_info.assert_called_once_with(
        "x@y.fr", identifier_type="email_id"
    )


@override_settings(BREVO_API_KEY="test-key")
def test_remove_contact_from_list_calls_sdk_with_ext_id_body(mock_brevo_sdk):
    sdk_instance = mock_brevo_sdk.return_value

    BrevoClient().remove_contact_from_list(ext_id="abc-123", list_id=42)

    sdk_instance.contacts.remove_contact_from_list.assert_called_once()
    args, kwargs = sdk_instance.contacts.remove_contact_from_list.call_args
    assert args == (42,)
    assert kwargs["request"].ext_ids == ["abc-123"]


@override_settings(BREVO_API_KEY="test-key")
def test_client_methods_return_sdk_response(mock_brevo_sdk):
    sdk_instance = mock_brevo_sdk.return_value
    sdk_instance.contacts.get_contact_info.return_value = "response"

    assert BrevoClient().get_contact(identifier="abc") == "response"


@override_settings(BREVO_API_KEY="test-key")
def test_update_contact_defaults_to_ext_id_identifier(mock_brevo_sdk):
    sdk_instance = mock_brevo_sdk.return_value

    BrevoClient().update_contact(
        identifier="abc-123",
        list_id=99,
        attributes={"EMAIL": "manon@example.com", "PRENOM": "Manon"},
    )

    sdk_instance.contacts.update_contact.assert_called_once_with(
        "abc-123",
        identifier_type="ext_id",
        attributes={"PRENOM": "Manon"},
        list_ids=[99],
    )


@override_settings(BREVO_API_KEY="test-key")
def test_update_contact_supports_email_id_identifier(mock_brevo_sdk):
    sdk_instance = mock_brevo_sdk.return_value

    BrevoClient().update_contact(
        identifier="manon@example.com",
        identifier_type="email_id",
        list_id=99,
        attributes={"PRENOM": "Manon"},
    )

    sdk_instance.contacts.update_contact.assert_called_once_with(
        "manon@example.com",
        identifier_type="email_id",
        attributes={"PRENOM": "Manon"},
        list_ids=[99],
    )
