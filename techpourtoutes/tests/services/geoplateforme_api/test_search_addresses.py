import httpx
import pytest

from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.geoplateforme_api.search_addresses import SearchAddresses

FEATURE = {
    "properties": {
        "id": "80021_6590_00008",
        "label": "8 Boulevard du Port 80000 Amiens",
        "name": "8 Boulevard du Port",
        "postcode": "80000",
        "city": "Amiens",
        "citycode": "80021",
    },
    "geometry": {"coordinates": [2.29009, 49.897443]},
}


def test_a_feature_becomes_a_flat_address(httpx_mock):
    httpx_mock.add_response(json={"features": [FEATURE]})

    result = SearchAddresses(query="8 boulevard du port")

    assert result.success
    assert result.addresses == [
        {
            "ban_id": "80021_6590_00008",
            "label": "8 Boulevard du Port 80000 Amiens",
            "address": "8 Boulevard du Port",
            "postal_code": "80000",
            "city": "Amiens",
            "cog_code": "80021",
            "longitude": 2.29009,
            "latitude": 49.897443,
        }
    ]


def test_a_feature_without_geometry_is_skipped(httpx_mock):
    """No coordinates means nothing to store: such a hit could never be approved."""
    httpx_mock.add_response(json={"features": [{"properties": {"id": "x"}, "geometry": {}}]})

    assert SearchAddresses(query="nulle part").addresses == []


def test_a_blank_query_never_reaches_the_api(httpx_mock):
    result = SearchAddresses(query="  ")

    assert result.success
    assert result.addresses == []
    assert not httpx_mock.get_requests()


@pytest.mark.parametrize("status_code", [429, 503])
def test_a_rate_limited_or_failing_api_is_a_transient_failure(httpx_mock, status_code):
    httpx_mock.add_response(status_code=status_code)

    result = SearchAddresses(query="8 boulevard du port")

    assert result.failure
    assert str(status_code) in result.errors[0]
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_network_error_is_a_transient_failure(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("boom"))

    result = SearchAddresses(query="8 boulevard du port")

    assert result.failure
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_client_error_is_not_worth_retrying(httpx_mock):
    httpx_mock.add_response(status_code=404)

    result = SearchAddresses(query="8 boulevard du port")

    assert result.failure
    assert result.error_kind is ErrorKind.PERMANENT


def test_an_unparsable_body_fails(httpx_mock):
    httpx_mock.add_response(content=b"<html>oops</html>")

    assert SearchAddresses(query="8 boulevard du port").failure
