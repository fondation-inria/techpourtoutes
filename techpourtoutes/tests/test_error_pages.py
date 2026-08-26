import re
from pathlib import Path

import pytest
from django.contrib.staticfiles import finders
from django.core.exceptions import PermissionDenied
from django.template.loader import get_template
from django.test import override_settings
from django.urls import include, path


def _forbidden(request):
    raise PermissionDenied()


def _crash(request):
    raise Exception("boom")


urlpatterns = [
    path("test-403/", _forbidden),
    path("test-500/", _crash),
    path("", include("conf.urls")),
]


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_404_page_renders(client):
    response = client.get("/url-that-does-not-exist-xyz/")
    assert response.status_code == 404
    assert b"introuvable" in response.content


@pytest.mark.django_db
@override_settings(DEBUG=False, ROOT_URLCONF=__name__)
def test_403_page_renders(client):
    response = client.get("/test-403/")
    assert response.status_code == 403
    assert b"autorisation" in response.content


@pytest.mark.django_db
@override_settings(DEBUG=False, ROOT_URLCONF=__name__)
def test_500_page_renders(client):
    client.raise_request_exception = False
    response = client.get("/test-500/")
    assert response.status_code == 500
    assert b"erreurs" in response.content


def test_500_page_holds_no_template_syntax():
    """handler500 renders without a request and without context processors, so
    anything resolved at render time is a chance to fail twice."""
    assert not re.search(r"{[%{#]", _template_source("500.html"))


def test_500_page_asset_paths_point_at_real_files():
    """Asset paths are hardcoded rather than resolved by the static tag, so
    moving a file would silently drop it. This test is the missing noise."""
    assets = re.findall(r'(?:src|href)="/static/([^"#]+)', _template_source("500.html"))
    assert assets
    assert [asset for asset in assets if finders.find(asset) is None] == []


def _template_source(name):
    return Path(get_template(name).origin.name).read_text()
