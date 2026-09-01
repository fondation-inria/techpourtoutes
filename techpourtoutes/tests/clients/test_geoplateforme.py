from techpourtoutes.clients.geoplateforme import BASE_URL, GeoplateformeClient


def test_search_addresses_asks_the_address_index(httpx_mock):
    httpx_mock.add_response(json={"features": []})

    GeoplateformeClient().search_addresses(query="8 boulevard du port")

    request = httpx_mock.get_request()
    assert request.url.path.endswith("/geocodage/search")
    assert request.url.params["q"] == "8 boulevard du port"
    assert request.url.params["index"] == "address"
    assert request.url.params["autocomplete"] == "1"
    assert BASE_URL.startswith("https://")
