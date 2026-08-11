import pytest


@pytest.mark.django_db
def test_robots_txt_returns_200(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain"


@pytest.mark.django_db
def test_robots_txt_content(client):
    content = client.get("/robots.txt").content.decode()
    assert "User-agent: *" in content
    assert "Sitemap:" in content
    assert "/sitemap.xml" in content


@pytest.mark.django_db
def test_robots_txt_disallows_private_pages(client):
    content = client.get("/robots.txt").content.decode()
    assert "Disallow: /mon-compte/" in content
    assert "Disallow: /mon-compte-mentor/" in content
    assert "Disallow: /bienvenue-dans-la-coalition/" in content
