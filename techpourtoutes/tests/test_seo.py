import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_favicon_uses_favicon_namefile_when_dynamic_favicon_disabled(client, settings):
    settings.FAVICON_DYNAMIC_ENABLED = False
    settings.FAVICON_NAMEFILE = "images/favicon-tpt-staging"
    content = client.get(reverse("mentions_legales")).content.decode()
    assert "favicon-tpt-staging.png" in content
    assert "favicon-tpt-coalition.svg" not in content
    assert "favicon-tpt-beneficiary.svg" not in content


@pytest.mark.django_db
def test_favicon_is_coalition_variant_on_coalition_page_when_dynamic_favicon_enabled(
    client, settings
):
    settings.FAVICON_DYNAMIC_ENABLED = True
    content = client.get(reverse("coalition_home")).content.decode()
    assert "favicon-tpt-coalition.svg" in content


@pytest.mark.django_db
def test_favicon_is_beneficiary_variant_on_beneficiary_page_when_dynamic_favicon_enabled(
    client, settings
):
    settings.FAVICON_DYNAMIC_ENABLED = True
    content = client.get(reverse("mentions_legales")).content.decode()
    assert "favicon-tpt-beneficiary.svg" in content


@pytest.mark.django_db
def test_home_page_has_unique_title(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert "<title>TechPourToutes</title>" not in content
    assert "<title>" in content


@pytest.mark.django_db
def test_home_page_has_meta_description(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert 'name="description"' in content


@pytest.mark.django_db
def test_base_template_has_lang_fr(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert 'lang="fr"' in content


@pytest.mark.django_db
def test_base_template_has_canonical(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert 'rel="canonical"' in content


@pytest.mark.django_db
def test_base_template_has_og_tags(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert 'property="og:title"' in content
    assert 'property="og:url"' in content
    assert 'property="og:image"' in content


@pytest.mark.django_db
def test_default_og_image_uses_coalition_cover(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert "coalition-tpt-white.png" in content


@pytest.mark.django_db
def test_notre_manifeste_og_image_uses_manifeste_cover(client):
    content = client.get(reverse("notre_manifeste")).content.decode()
    assert "manifeste-tpt-cover-white.png" in content
