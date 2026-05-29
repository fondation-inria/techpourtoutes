from unittest.mock import MagicMock, patch

import httpx
import pytest
from django.test import override_settings

from techpourtoutes.services.base import BaseService, FailedServiceError
from techpourtoutes.services.jobirl_api.base_service import (
    NETWORK_ERROR_MESSAGE,
    JobirlApiBaseService,
)

# --- BaseService ---


class SuccessService(BaseService):
    def perform(self, **kwargs):
        self.received_kwargs = kwargs


class FailingService(BaseService):
    def perform(self, **kwargs):
        self.fail(kwargs.get("message", "something went wrong"))


def test_base_service_success():
    result = SuccessService(foo="bar")

    assert result.success is True
    assert result.failure is False
    assert result.errors == []


def test_base_service_forwards_kwargs_to_perform():
    result = SuccessService(foo="bar", baz=42)

    assert result.received_kwargs == {"foo": "bar", "baz": 42}


def test_base_service_failure_sets_state():
    result = FailingService(message="oops")

    assert result.success is False
    assert result.failure is True
    assert result.errors == ["oops"]


def test_base_service_fail_with_no_message():
    result = FailingService()

    assert result.failure is True
    assert result.errors == ["something went wrong"]


def test_base_service_fail_raises_failed_service_error():
    service = object.__new__(SuccessService)
    service.errors = []

    with pytest.raises(FailedServiceError, match="bad"):
        service.fail("bad")


def test_base_service_perform_not_implemented():
    with pytest.raises(NotImplementedError):
        BaseService()


# --- JobirlApiBaseService ---


class SimpleJobirlService(JobirlApiBaseService):
    def perform(self, *, path="endpoint"):
        self.request(method="post", path=path)


def _mock_jobirl_response(*, status_code=200, json_body=None):
    response = MagicMock()
    response.is_success = 200 <= status_code < 300
    response.status_code = status_code
    response.json.return_value = json_body or {}
    return response


def _make_service(response):
    with patch("techpourtoutes.services.jobirl_api.base_service.JobirlClient") as MockClient:
        MockClient.return_value.post.return_value = response
        return SimpleJobirlService()


def test_jobirl_api_success_exposes_response_body():
    response = _mock_jobirl_response(json_body={"datas": {"id": 1, "token": "tok"}})
    result = _make_service(response)

    assert result.success is True
    assert result.jobirl_response_body == {"id": 1, "token": "tok"}


def test_jobirl_api_response_body_defaults_to_empty_dict_when_no_datas_key():
    response = _mock_jobirl_response(json_body={"response": "success"})
    result = _make_service(response)

    assert result.success is True
    assert result.jobirl_response_body == {}


def test_jobirl_api_http_error_sets_failure():
    response = _mock_jobirl_response(status_code=500)
    result = _make_service(response)

    assert result.failure is True
    assert "500" in result.errors[0]


def test_jobirl_api_4xx_includes_detail_from_response():
    response = _mock_jobirl_response(
        status_code=400,
        json_body={"datas": {"message": "EMAIL ALREADY EXISTS"}},
    )
    result = _make_service(response)

    assert result.failure is True
    joined = " ".join(result.errors)
    assert "400" in joined
    assert "EMAIL ALREADY EXISTS" in joined


def test_jobirl_api_4xx_without_detail_omits_detail_suffix():
    response = _mock_jobirl_response(
        status_code=422,
        json_body={"datas": {"message": ""}},
    )
    result = _make_service(response)

    assert result.failure is True
    assert "Détails" not in result.errors[0]


def test_jobirl_api_network_error_sets_failure():
    with patch("techpourtoutes.services.jobirl_api.base_service.JobirlClient") as MockClient:
        MockClient.return_value.post.side_effect = httpx.RequestError("connection refused")
        result = SimpleJobirlService()

    assert result.failure is True
    assert result.errors[0] == NETWORK_ERROR_MESSAGE


# --- CreateMentor ---


def _mock_jobirl_registration(*, success=True, user_id=287565, token="tpt_abc", errors=None):
    return MagicMock(
        success=success,
        failure=not success,
        errors=errors or [],
        user_id=user_id if success else None,
        token=token if success else None,
    )


def _unsaved_pro(valid_pro_model_data):
    from techpourtoutes.models import Pro

    return Pro(**valid_pro_model_data, username=valid_pro_model_data["email"])


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_calls_jobirl_with_mentor(valid_pro_model_data):
    from techpourtoutes.services.create_mentor import CreateMentor

    pro = _unsaved_pro(valid_pro_model_data)
    mock = _mock_jobirl_registration()

    with patch(
        "techpourtoutes.services.create_mentor.RegisterMentorOnJobirl", return_value=mock
    ) as MockRegister:
        CreateMentor(pro=pro)

    MockRegister.assert_called_once_with(pro=pro)


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_saves_mentor_with_jobirl_fields(valid_pro_model_data):
    from techpourtoutes.models import Pro
    from techpourtoutes.services.create_mentor import CreateMentor

    pro = _unsaved_pro(valid_pro_model_data)
    mock = _mock_jobirl_registration()

    with patch("techpourtoutes.services.create_mentor.RegisterMentorOnJobirl", return_value=mock):
        result = CreateMentor(pro=pro)

    assert result.success is True
    db_pro = Pro.objects.get(email=valid_pro_model_data["email"])
    assert db_pro.jobirl_user_id == 287565
    assert db_pro.jobirl_user_token == "tpt_abc"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_sends_welcome_email(valid_pro_model_data):
    from django.core import mail

    from techpourtoutes.services.create_mentor import CreateMentor

    pro = _unsaved_pro(valid_pro_model_data)
    mock = _mock_jobirl_registration()

    with patch("techpourtoutes.services.create_mentor.RegisterMentorOnJobirl", return_value=mock):
        CreateMentor(pro=pro)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [valid_pro_model_data["email"]]
    assert "Bienvenue" in mail.outbox[0].subject


@pytest.mark.django_db
def test_create_mentor_on_jobirl_failure_propagates_errors(valid_pro_model_data):
    from techpourtoutes.models import Pro
    from techpourtoutes.services.create_mentor import CreateMentor

    pro = _unsaved_pro(valid_pro_model_data)
    mock = _mock_jobirl_registration(success=False, errors=["erreur de synchronisation"])

    with patch("techpourtoutes.services.create_mentor.RegisterMentorOnJobirl", return_value=mock):
        result = CreateMentor(pro=pro)

    assert result.failure is True
    assert result.errors == ["erreur de synchronisation"]
    assert not Pro.objects.filter(email=valid_pro_model_data["email"]).exists()


@pytest.mark.django_db(transaction=True)
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_syncs_contact_to_brevo(valid_pro_model_data, mock_brevo_sdk):
    from techpourtoutes.services.create_mentor import CreateMentor

    pro = _unsaved_pro(valid_pro_model_data)
    mock = _mock_jobirl_registration()

    with patch("techpourtoutes.services.create_mentor.RegisterMentorOnJobirl", return_value=mock):
        result = CreateMentor(pro=pro)

    assert result.success is True
    create_contact = mock_brevo_sdk.return_value.contacts.create_contact
    create_contact.assert_called()
    call_kwargs = create_contact.call_args.kwargs
    assert call_kwargs["email"] == valid_pro_model_data["email"]
    assert call_kwargs["ext_id"] == str(pro.pk)
    assert call_kwargs["update_enabled"] is True
    assert call_kwargs["list_ids"] == [42]
    assert call_kwargs["attributes"]["PRENOM"] == valid_pro_model_data["first_name"]
    assert call_kwargs["attributes"]["NOM"] == valid_pro_model_data["last_name"]
