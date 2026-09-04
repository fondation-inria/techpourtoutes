from techpourtoutes.clients.geoplateforme import BASE_URL, GeoplateformeClient


def test_search_addresses_queries_the_index_it_is_given(httpx_mock):
    """The two indexes are asked separately, so the caller says which one and how many."""
    httpx_mock.add_response(json={"features": []})

    GeoplateformeClient().search_addresses(query="station f", index="poi", limit=50)

    request = httpx_mock.get_request()
    assert request.url.path.endswith("/geocodage/search")
    assert request.url.params["q"] == "station f"
    assert request.url.params["index"] == "poi"
    assert request.url.params["limit"] == "50"
    assert request.url.params["autocomplete"] == "1"
    assert BASE_URL.startswith("https://")
