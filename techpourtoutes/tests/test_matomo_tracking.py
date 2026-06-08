from django.test import override_settings
from django.urls import reverse


@override_settings(MATOMO_URL="https://matomo.example.test", MATOMO_SITE_ID="42")
def test_matomo_snippet_rendered_when_configured(client):
    content = client.get(reverse("notre_manifeste")).content.decode()
    assert 'var u="https://matomo.example.test/"' in content
    assert "_paq.push(['setSiteId', '42'])" in content
    assert "_paq.push(['disableCookies'])" in content


@override_settings(MATOMO_URL="", MATOMO_SITE_ID="")
def test_matomo_snippet_absent_when_not_configured(client):
    content = client.get(reverse("notre_manifeste")).content.decode()
    assert "matomo" not in content.lower()
