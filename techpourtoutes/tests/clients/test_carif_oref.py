import json

from techpourtoutes.clients.carif_oref import CarifOrefClient

FORMATIONS_URL = "https://catalogue-apprentissage.intercariforef.org/api/v1/entity/formations"


def test_carif_oref_client_fetches_a_page_of_formations(httpx_mock):
    httpx_mock.add_response(json={"formations": []})

    response = CarifOrefClient().fetch_formations(page=2, limit=1000)

    assert response.is_success
    request = httpx_mock.get_request()
    assert request.method == "GET"
    assert str(request.url).startswith(FORMATIONS_URL)
    assert request.url.params["page"] == "2"
    assert request.url.params["limit"] == "1000"


def test_the_client_asks_for_the_published_perimeter_explicitly(httpx_mock):
    """Left implicit, the filter silently lapses the day a `query` is added."""
    httpx_mock.add_response(json={"formations": []})

    CarifOrefClient().fetch_formations(page=1, limit=1000)

    query = json.loads(httpx_mock.get_request().url.params["query"])
    assert query == {"published": True, "catalogue_published": True}


def test_the_client_projects_the_fields_the_mapper_reads(httpx_mock):
    """Whole records blow past 20 MB a page and the response truncates mid-stream."""
    httpx_mock.add_response(json={"formations": []})

    CarifOrefClient().fetch_formations(page=1, limit=1000)

    select = json.loads(httpx_mock.get_request().url.params["select"])
    assert select["onisep_url"] == 1
    assert select["rncp_details.nsf_code"] == 1
    assert select["etablissement_gestionnaire_uai"] == 1
