import pytest

COALITION_OLD_HOST = "coalition.techpourtoutes.io"


@pytest.fixture(autouse=True)
def coalition_host(settings):
    settings.ALLOWED_HOSTS = ["testserver", COALITION_OLD_HOST]
    settings.COALITION_OLD_HOST = COALITION_OLD_HOST
    settings.SITE_URL = "https://techpourtoutes.io"


def test_coalition_host_redirects_root_to_coalition_home(client):
    response = client.get("/", HTTP_HOST=COALITION_OLD_HOST)

    assert response.status_code == 301
    assert response["Location"] == "https://techpourtoutes.io/coalition/"


def test_coalition_host_keeps_the_path_and_query_string(client):
    response = client.get("/mentorer/?utm_source=flyer", HTTP_HOST=COALITION_OLD_HOST)

    assert response.status_code == 301
    assert response["Location"] == "https://techpourtoutes.io/coalition/mentorer/?utm_source=flyer"


def test_coalition_host_redirects_unknown_path_to_coalition_home(client):
    response = client.get("/n-existe-pas/", HTTP_HOST=COALITION_OLD_HOST)

    assert response.status_code == 301
    assert response["Location"] == "https://techpourtoutes.io/coalition/"


@pytest.mark.django_db
def test_other_hosts_are_not_redirected(client):
    response = client.get("/mentorer/")

    assert response.status_code == 404
