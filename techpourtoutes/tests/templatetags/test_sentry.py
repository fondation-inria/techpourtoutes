import pytest
from django.test import override_settings
from django.urls import reverse

DSN = "https://public@o1.ingest.de.sentry.io/2"


@pytest.mark.django_db
@override_settings(SENTRY_DSN=DSN)
def test_sentry_browser_sdk_rendered_when_configured(client):
    content = client.get(reverse("notre_manifeste")).content.decode()
    assert "js/sentry.min.js" in content
    assert "js/sentry_init.js" in content
    assert f'data-dsn="{DSN}"' in content


@pytest.mark.django_db
@override_settings(SENTRY_DSN="")
def test_sentry_browser_sdk_absent_when_not_configured(client):
    content = client.get(reverse("notre_manifeste")).content.decode()
    assert "sentry" not in content.lower()
