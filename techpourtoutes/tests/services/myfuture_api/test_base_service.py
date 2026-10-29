import httpx

from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.myfuture_api.fetch_job_postings import FetchMyFutureJobPostings


def test_an_http_error_is_a_transient_failure(httpx_mock):
    httpx_mock.add_response(status_code=503)

    result = FetchMyFutureJobPostings()

    assert result.failure
    assert "503" in result.errors[0]
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_rate_limited_page_is_a_transient_failure(httpx_mock):
    httpx_mock.add_response(status_code=429)

    result = FetchMyFutureJobPostings()

    assert result.failure
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_network_error_is_a_transient_failure(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("boom"))

    result = FetchMyFutureJobPostings()

    assert result.failure
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_refused_key_is_not_worth_retrying(httpx_mock):
    httpx_mock.add_response(status_code=401)

    result = FetchMyFutureJobPostings()

    assert result.failure
    assert result.error_kind is ErrorKind.PERMANENT


def test_an_unparsable_body_fails_without_records(httpx_mock):
    httpx_mock.add_response(status_code=200, content=b"<html>oops</html>")

    result = FetchMyFutureJobPostings()

    assert result.failure
    assert result.myfuture_records == []
