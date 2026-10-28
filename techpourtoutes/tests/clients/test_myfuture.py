from django.test import override_settings

from techpourtoutes.clients.myfuture import MyFutureClient

OFFERS_URL = "https://api.myfutu.re/api/offers"


@override_settings(MYFUTURE_API_KEY="secret")
def test_the_client_fetches_a_page_of_an_endpoint_with_its_bearer_token(httpx_mock):
    httpx_mock.add_response(json=[])

    response = MyFutureClient().fetch_offers(
        endpoint="offers", sub_domain_keys=["sciencesmathematiques"], offset=2000, limit=1000
    )

    assert response.is_success
    request = httpx_mock.get_request()
    assert request.method == "GET"
    assert str(request.url).startswith(OFFERS_URL)
    assert request.headers["Authorization"] == "Bearer secret"
    assert request.url.params["offset"] == "2000"
    assert request.url.params["limit"] == "1000"


def test_the_sub_domains_are_sent_comma_separated(httpx_mock):
    httpx_mock.add_response(json=[])

    MyFutureClient().fetch_offers(
        endpoint="internships",
        sub_domain_keys=["sciencesmathematiques", "sciencessciences-de-lunivers"],
        offset=0,
        limit=1000,
    )

    params = httpx_mock.get_request().url.params
    assert params["subDomainKeys"] == "sciencesmathematiques,sciencessciences-de-lunivers"
