from unittest.mock import MagicMock, patch

import httpx
import pytest

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
