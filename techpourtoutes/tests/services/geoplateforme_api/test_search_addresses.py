import httpx
import pytest

from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.geoplateforme_api.search_addresses import SearchAddresses

FEATURE = {
    "properties": {
        "_type": "address",
        "id": "80021_6590_00008",
        "label": "8 Boulevard du Port 80000 Amiens",
        "name": "8 Boulevard du Port",
        "postcode": "80000",
        "city": "Amiens",
        "citycode": "80021",
        "score": 0.97,
    },
    "geometry": {"coordinates": [2.29009, 49.897443]},
}

# The POI index answers with arrays — a site can straddle several communes — and names its
# hit `toponym`: it holds no street address at all.
POI_FEATURE = {
    "properties": {
        "_type": "poi",
        "toponym": "Station F",
        "postcode": ["75013"],
        "city": ["Paris 13e Arrondissement", "Paris"],
        "citycode": ["75113", "75056"],
        "category": ["zone industrielle"],
        "extrafields": {"cleabs": "SURFACTI0000002006279671"},
        "score": 0.31,
    },
    "geometry": {"coordinates": [2.371699, 48.833436]},
}


def test_a_feature_becomes_a_flat_address(mock_geocoding):
    mock_geocoding(addresses=[FEATURE])

    result = SearchAddresses(query="8 boulevard du port")

    assert result.success
    assert result.addresses == [
        {
            "ban_id": "80021_6590_00008",
            "label": "8 Boulevard du Port 80000 Amiens",
            "poi_name": "",
            "address": "8 Boulevard du Port",
            "postal_code": "80000",
            "city": "Amiens",
            "cog_code": "80021",
            "longitude": 2.29009,
            "latitude": 49.897443,
        }
    ]


def test_a_poi_becomes_a_named_venue_without_a_street(mock_geocoding):
    mock_geocoding(pois=[POI_FEATURE])

    result = SearchAddresses(query="station f")

    assert result.addresses == [
        {
            "ban_id": "",
            "label": "Station F, Paris 13e Arrondissement",
            "poi_name": "Station F",
            "address": "",
            "postal_code": "75013",
            "city": "Paris 13e Arrondissement",
            "cog_code": "75113",
            "longitude": 2.371699,
            "latitude": 48.833436,
        }
    ]


def test_a_poi_keeps_the_first_of_several_postcodes(mock_geocoding):
    """The array is then the whole commune's list; the first is better than none at all."""
    properties = POI_FEATURE["properties"] | {"postcode": ["59000", "59800"], "city": ["Lille"]}
    mock_geocoding(pois=[POI_FEATURE | {"properties": properties}])

    address = SearchAddresses(query="mairie de lille").addresses[0]

    assert address["postal_code"] == "59000"
    assert address["label"] == "Station F, Lille"


def test_both_indexes_are_asked_separately(httpx_mock, mock_geocoding):
    """Asked together, a query naming a venue and its city ranks every street of that city
    above the venue, and the venue falls off the end of the list."""
    mock_geocoding(addresses=[FEATURE], pois=[POI_FEATURE])

    SearchAddresses(query="station f paris")

    assert sorted(request.url.params["index"] for request in httpx_mock.get_requests()) == [
        "address",
        "poi",
    ]


def test_venues_lead_when_no_address_is_a_real_match(mock_geocoding):
    """ "station f paris" makes every street of Paris score just above the venue. Those are all
    noise, and their scores say so: none of them looks like a typed address."""
    noise = [
        FEATURE | {"properties": FEATURE["properties"] | {"label": f"Voie F/{n}", "score": 0.34}}
        for n in range(5)
    ]
    mock_geocoding(addresses=noise, pois=[POI_FEATURE])

    labels = [address["label"] for address in SearchAddresses(query="station f paris").addresses]

    assert labels[0] == "Station F, Paris 13e Arrondissement"
    assert labels[1:] == [f"Voie F/{n}" for n in range(5)]


def test_addresses_lead_when_one_of_them_is_a_real_match(mock_geocoding):
    mock_geocoding(addresses=[FEATURE], pois=[POI_FEATURE])

    result = SearchAddresses(query="8 boulevard du port amiens")
    labels = [address["label"] for address in result.addresses]

    assert labels == ["8 Boulevard du Port 80000 Amiens", "Station F, Paris 13e Arrondissement"]


def test_each_section_keeps_the_order_the_api_gave_it(mock_geocoding):
    """Scores from two indexes are not comparable, so the lists are never interleaved."""
    addresses = [
        FEATURE | {"properties": FEATURE["properties"] | {"label": label, "score": score}}
        for label, score in [("proche", 0.98), ("moins proche", 0.5)]
    ]
    mock_geocoding(addresses=addresses, pois=[POI_FEATURE])

    result = SearchAddresses(query="8 boulevard du port amiens")

    assert [address["label"] for address in result.addresses[:2]] == ["proche", "moins proche"]


def test_an_address_hit_carries_no_poi_name(mock_geocoding):
    mock_geocoding(addresses=[FEATURE])

    assert SearchAddresses(query="8 boulevard du port").addresses[0]["poi_name"] == ""


def test_a_feature_without_geometry_is_skipped(mock_geocoding):
    """No coordinates means nothing to store: such a hit could never be approved."""
    mock_geocoding(addresses=[{"properties": {"id": "x"}, "geometry": {}}])

    assert SearchAddresses(query="nulle part").addresses == []


@pytest.mark.parametrize("query", ["  ", "8", "8 "])
def test_a_query_too_short_for_the_api_never_reaches_it(httpx_mock, query):
    """The API rejects anything under three characters with a 400: that is not a failure."""
    result = SearchAddresses(query=query)

    assert result.success
    assert result.addresses == []
    assert not httpx_mock.get_requests()


@pytest.mark.parametrize("status_code", [429, 503])
def test_a_rate_limited_or_failing_api_is_a_transient_failure(httpx_mock, status_code):
    httpx_mock.add_response(status_code=status_code, is_reusable=True)

    result = SearchAddresses(query="8 boulevard du port")

    assert result.failure
    assert str(status_code) in result.errors[0]
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_network_error_is_a_transient_failure(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("boom"), is_reusable=True)

    result = SearchAddresses(query="8 boulevard du port")

    assert result.failure
    assert result.error_kind is ErrorKind.TRANSIENT


def test_a_client_error_is_not_worth_retrying(httpx_mock):
    httpx_mock.add_response(status_code=404, is_reusable=True)

    result = SearchAddresses(query="8 boulevard du port")

    assert result.failure
    assert result.error_kind is ErrorKind.PERMANENT


def test_an_unparsable_body_fails(httpx_mock):
    httpx_mock.add_response(content=b"<html>oops</html>", is_reusable=True)

    assert SearchAddresses(query="8 boulevard du port").failure
