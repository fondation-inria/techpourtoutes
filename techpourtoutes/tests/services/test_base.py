import pytest

from techpourtoutes.services.base import BaseService, FailedServiceError


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
