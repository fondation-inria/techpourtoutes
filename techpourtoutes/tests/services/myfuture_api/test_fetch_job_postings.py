from unittest.mock import patch

from techpourtoutes.services.myfuture_api.fetch_job_postings import FetchMyFutureJobPostings
from techpourtoutes.utils.myfuture import SUB_DOMAINS


def _offers(*ids):
    return [{"_id": external_id} for external_id in ids]


def test_both_endpoints_are_walked_until_a_short_page(httpx_mock):
    httpx_mock.add_response(json=_offers("a", "b"))
    httpx_mock.add_response(json=_offers("c"))
    httpx_mock.add_response(json=_offers("d"))

    with patch.object(FetchMyFutureJobPostings, "PAGE_SIZE", 2):
        result = FetchMyFutureJobPostings()

    assert result.success
    assert [record["_id"] for record in result.myfuture_records] == ["a", "b", "c", "d"]
    requests = httpx_mock.get_requests()
    assert [request.url.path for request in requests] == [
        "/api/offers",
        "/api/offers",
        "/api/internships",
    ]
    assert [request.url.params["offset"] for request in requests] == ["0", "2", "0"]


def test_an_offer_listed_on_both_endpoints_comes_back_once(httpx_mock):
    httpx_mock.add_response(json=_offers("a", "b"))
    httpx_mock.add_response(json=_offers("b"))

    result = FetchMyFutureJobPostings()

    assert [record["_id"] for record in result.myfuture_records] == ["a", "b"]


def test_only_the_sub_domains_we_follow_are_asked_for(httpx_mock):
    httpx_mock.add_response(json=[])
    httpx_mock.add_response(json=[])

    FetchMyFutureJobPostings()

    for request in httpx_mock.get_requests():
        assert request.url.params["subDomainKeys"].split(",") == list(SUB_DOMAINS)


def test_a_page_that_fails_stops_the_walk(httpx_mock):
    httpx_mock.add_response(json=_offers("a", "b"))
    httpx_mock.add_response(status_code=503)

    with patch.object(FetchMyFutureJobPostings, "PAGE_SIZE", 2):
        result = FetchMyFutureJobPostings()

    assert result.failure
    assert len(httpx_mock.get_requests()) == 2
