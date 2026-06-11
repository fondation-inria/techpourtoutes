import pytest
from django.urls import reverse


def test_robots_txt_returns_200(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain"


def test_robots_txt_content(client):
    content = client.get("/robots.txt").content.decode()
    assert "User-agent: *" in content
    assert "Sitemap:" in content
    assert "/sitemap.xml" in content


def test_robots_txt_disallows_private_pages(client):
    content = client.get("/robots.txt").content.decode()
    assert "Disallow: /mon-compte/" in content
    assert "Disallow: /mon-compte-mentor/" in content
    assert "Disallow: /bienvenue-dans-la-coalition/" in content


@pytest.mark.django_db
def test_sitemap_returns_200(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200


@pytest.mark.django_db
def test_sitemap_contains_public_urls(client):
    content = client.get("/sitemap.xml").content.decode()
    assert reverse("coalition_home") in content
    assert reverse("mentor_landing") in content
    assert reverse("notre_manifeste") in content


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
