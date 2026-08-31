import httpx

from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.carif_oref_api.fetch_formations import FetchCarifOrefFormations


def _page(formations, *, pages=1):
    return {"formations": formations, "pagination": {"nombre_de_page": pages}}


def test_a_successful_fetch_exposes_the_records(httpx_mock):
    httpx_mock.add_response(json=_page([{"intitule_rco": "BTS"}]))

    result = FetchCarifOrefFormations()

    assert result.success
    assert result.carif_oref_records == [{"intitule_rco": "BTS"}]


def test_an_http_error_is_a_transient_failure(httpx_mock):
    httpx_mock.add_response(status_code=503)

    result = FetchCarifOrefFormations()

    assert result.failure
    assert "503" in result.errors[0]
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_rate_limited_page_is_a_transient_failure(httpx_mock):
    httpx_mock.add_response(status_code=429)

    result = FetchCarifOrefFormations()

    assert result.failure
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_network_error_is_a_transient_failure(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("boom"))

    result = FetchCarifOrefFormations()

    assert result.failure
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_client_error_is_not_worth_retrying(httpx_mock):
    httpx_mock.add_response(status_code=404)

    result = FetchCarifOrefFormations()

    assert result.failure
    assert result.error_kind is ErrorKind.PERMANENT


def test_an_unparsable_body_fails_without_records(httpx_mock):
    httpx_mock.add_response(status_code=200, content=b"<html>oops</html>")

    result = FetchCarifOrefFormations()

    assert result.failure
    assert result.carif_oref_records == []
