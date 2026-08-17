import pytest

from techpourtoutes.services.base_api import BaseApiService


class Upstream(BaseApiService):
    """Stands in for a service that talked to an API and failed."""

    def perform(self, *, message, status_code=None, network_error=False) -> None:
        self.status_code = status_code
        self.network_error = network_error
        self.fail(message)


class Orchestrator(BaseApiService):
    """Stands in for a service that only relays someone else's failure."""

    def perform(self, *, upstream) -> None:
        self.fail_with_errors(upstream)


def test_a_fresh_service_carries_no_failure():
    service = BaseApiService.__new__(BaseApiService)

    assert service.status_code is None
    assert service.network_error is False


def test_fail_with_errors_adopts_the_upstream_failure():
    upstream = Upstream(message="Le téléchargement a échoué (code 503).", status_code=503)

    result = Orchestrator(upstream=upstream)

    assert result.failure
    assert result.errors == ["Le téléchargement a échoué (code 503)."]
    assert result.status_code == 503
    assert result.network_error is False


def test_fail_with_errors_carries_a_network_failure_too():
    upstream = Upstream(message="Injoignable.", network_error=True)

    result = Orchestrator(upstream=upstream)

    assert result.network_error is True
    assert result.failed_with_transient_error()


def test_fail_with_errors_joins_several_messages():
    upstream = Upstream(message="premier")
    upstream.errors.append("second")

    result = Orchestrator(upstream=upstream)

    assert result.errors == ["premier, second"]


@pytest.mark.parametrize(
    "status_code,network_error,expected",
    [
        (None, True, True),
        (429, False, True),
        (500, False, True),
        (503, False, True),
        (404, False, False),
        (400, False, False),
        (None, False, False),
    ],
)
def test_failed_with_transient_error(status_code, network_error, expected):
    service = Upstream(message="boum", status_code=status_code, network_error=network_error)

    assert service.failed_with_transient_error() is expected
