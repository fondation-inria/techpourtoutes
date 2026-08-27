import pytest

from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.base_api import BaseApiService


class Upstream(BaseApiService):
    """Stands in for a service that talked to an API and failed."""

    def perform(self, *, message, status_code=None, network_error=False) -> None:
        self.status_code = status_code
        self.network_error = network_error
        self.fail(message)


def test_a_fresh_service_carries_no_failure():
    service = BaseApiService.__new__(BaseApiService)

    assert service.status_code is None
    assert service.network_error is False
    assert service.error_kind is ErrorKind.PERMANENT


def test_an_api_failure_keeps_the_response_it_came_from():
    result = Upstream(message="Le téléchargement a échoué (code 503).", status_code=503)

    assert result.failure
    assert result.errors == ["Le téléchargement a échoué (code 503)."]
    assert result.status_code == 503
    assert result.network_error is False


@pytest.mark.parametrize(
    "status_code,network_error,expected",
    [
        (None, True, ErrorKind.TRANSIENT),
        (429, False, ErrorKind.TRANSIENT),
        (500, False, ErrorKind.TRANSIENT),
        (503, False, ErrorKind.TRANSIENT),
        (404, False, ErrorKind.PERMANENT),
        (400, False, ErrorKind.PERMANENT),
        (None, False, ErrorKind.PERMANENT),
    ],
)
def test_the_kind_is_read_off_the_response(status_code, network_error, expected):
    service = Upstream(message="boum", status_code=status_code, network_error=network_error)

    assert service.error_kind is expected
