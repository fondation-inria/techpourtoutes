import pytest
from django.test import RequestFactory

from techpourtoutes.utils.urls import safe_url


@pytest.mark.parametrize(
    "candidate",
    ["/stages-alternances-emplois/?q=data", "http://testserver/evenements/?page=2"],
)
def test_safe_url_keeps_a_url_on_the_site(candidate):
    assert safe_url(RequestFactory().get("/"), candidate) == candidate


@pytest.mark.parametrize("candidate", ["", "https://evil.example/", "//evil.example/"])
def test_safe_url_drops_a_url_leaving_the_site(candidate):
    assert safe_url(RequestFactory().get("/"), candidate) == ""


def test_safe_url_drops_plain_http_on_a_secure_request():
    request = RequestFactory().get("/", secure=True)

    assert safe_url(request, "http://testserver/") == ""
