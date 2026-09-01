from techpourtoutes.services.carif_oref_api.fetch_formations import FetchCarifOrefFormations


def _page(formations, *, pages):
    return {"formations": formations, "pagination": {"nombre_de_page": pages}}


def test_every_page_announced_is_fetched_and_accumulated(httpx_mock):
    httpx_mock.add_response(json=_page([{"intitule_rco": "un"}], pages=3))
    httpx_mock.add_response(json=_page([{"intitule_rco": "deux"}], pages=3))
    httpx_mock.add_response(json=_page([{"intitule_rco": "trois"}], pages=3))

    result = FetchCarifOrefFormations()

    assert result.success
    assert [record["intitule_rco"] for record in result.carif_oref_records] == [
        "un",
        "deux",
        "trois",
    ]
    assert [request.url.params["page"] for request in httpx_mock.get_requests()] == ["1", "2", "3"]


def test_a_single_page_catalogue_is_not_asked_twice(httpx_mock):
    httpx_mock.add_response(json=_page([{"intitule_rco": "un"}], pages=1))

    FetchCarifOrefFormations()

    assert len(httpx_mock.get_requests()) == 1


def test_a_page_that_fails_stops_the_walk(httpx_mock):
    httpx_mock.add_response(json=_page([{"intitule_rco": "un"}], pages=3))
    httpx_mock.add_response(status_code=503)

    result = FetchCarifOrefFormations()

    assert result.failure
    assert len(httpx_mock.get_requests()) == 2
