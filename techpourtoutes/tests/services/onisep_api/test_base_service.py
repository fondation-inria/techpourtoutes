import httpx

from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.onisep_api.fetch_formations import FetchOnisepFormations

DATASET_URL = "https://api.opendata.onisep.fr/downloads/5fa591127f501/5fa591127f501.json"


def test_a_successful_download_exposes_the_records(httpx_mock):
    httpx_mock.add_response(url=DATASET_URL, status_code=200, json=[{"code_nsf": "314"}])

    result = FetchOnisepFormations()

    assert result.success
    assert result.onisep_records == [{"code_nsf": "314"}]


def test_an_http_error_is_a_transient_failure(httpx_mock):
    httpx_mock.add_response(url=DATASET_URL, status_code=503)

    result = FetchOnisepFormations()

    assert result.failure
    assert "503" in result.errors[0]
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_network_error_is_a_transient_failure(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("boom"))

    result = FetchOnisepFormations()

    assert result.failure
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_client_error_is_not_worth_retrying(httpx_mock):
    httpx_mock.add_response(url=DATASET_URL, status_code=404)

    result = FetchOnisepFormations()

    assert result.failure
    assert result.error_kind is ErrorKind.PERMANENT


def test_an_unparsable_body_fails_without_records(httpx_mock):
    httpx_mock.add_response(url=DATASET_URL, status_code=200, content=b"<html>oops</html>")

    result = FetchOnisepFormations()

    assert result.failure
    assert result.onisep_records == []
