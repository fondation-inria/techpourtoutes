import pytest

from techpourtoutes.services.base import BaseService, ErrorKind, FailedServiceError


class SuccessService(BaseService):
    def perform(self, **kwargs):
        self.received_kwargs = kwargs


class FailingService(BaseService):
    def perform(self, *, message="something went wrong", kind=ErrorKind.PERMANENT):
        self.fail(message, kind=kind)


class RelayingService(BaseService):
    def perform(self, *, upstream):
        self.fail_with_errors(upstream)


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


def test_base_service_failure_is_permanent_by_default():
    result = FailingService()

    assert result.error_kind is ErrorKind.PERMANENT
    assert result.failed_with_transient_error is False


def test_base_service_fail_records_the_kind_it_was_given():
    result = FailingService(kind=ErrorKind.TRANSIENT)

    assert result.error_kind is ErrorKind.TRANSIENT
    assert result.failed_with_transient_error is True


def test_fail_with_errors_adopts_the_upstream_messages_and_kind():
    upstream = FailingService(message="Injoignable.", kind=ErrorKind.TRANSIENT)

    result = RelayingService(upstream=upstream)

    assert result.failure is True
    assert result.errors == ["Injoignable."]
    assert result.error_kind is ErrorKind.TRANSIENT


def test_fail_with_errors_joins_several_messages():
    upstream = FailingService(message="premier")
    upstream.errors.append("second")

    result = RelayingService(upstream=upstream)

    assert result.errors == ["premier, second"]
