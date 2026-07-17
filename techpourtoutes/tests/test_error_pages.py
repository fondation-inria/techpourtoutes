import pytest
from django.core.exceptions import PermissionDenied
from django.test import override_settings
from django.urls import include, path


def _forbidden(request):
    raise PermissionDenied()


urlpatterns = [
    path("test-403/", _forbidden),
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
    assert b"refus" in response.content
