import pytest
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from techpourtoutes.utils.local_upload import sign_local_upload_policy

KEY = "events/abc.png"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _post(
    client,
    *,
    content=b"png",
    content_type="image/png",
    storage_alias="public",
    policy_alias="public",
):
    policy = sign_local_upload_policy(
        storage_alias=policy_alias, key=KEY, content_type="image/png", max_size=5
    )
    return client.post(
        reverse("create_local_upload", args=[storage_alias]),
        {
            "key": KEY,
            "Content-Type": content_type,
            "policy": policy,
            "file": SimpleUploadedFile("photo.png", content),
        },
    )


def test_create_local_upload_stores_the_file_under_the_signed_key(client):
    response = _post(client)

    assert response.status_code == 204
    assert storages["public"].open(KEY).read() == b"png"


def test_create_local_upload_needs_no_csrf_token_like_a_bucket():
    assert _post(Client(enforce_csrf_checks=True)).status_code == 204


def test_create_local_upload_refuses_an_oversized_file(client):
    response = _post(client, content=b"too big")

    assert response.status_code == 400
    assert not storages["public"].exists(KEY)


def test_create_local_upload_refuses_an_empty_file(client):
    assert _post(client, content=b"").status_code == 400


def test_create_local_upload_refuses_a_tampered_policy(client):
    response = client.post(
        reverse("create_local_upload", args=["public"]),
        {"policy": "forged", "file": SimpleUploadedFile("photo.png", b"png")},
    )

    assert response.status_code == 403


def test_create_local_upload_refuses_a_policy_signed_for_another_storage(client):
    assert _post(client, storage_alias="public", policy_alias="default").status_code == 403


def test_create_local_upload_refuses_a_content_type_other_than_the_signed_one(client):
    response = _post(client, content_type="text/html")

    assert response.status_code == 403
    assert not storages["public"].exists(KEY)


def test_create_local_upload_does_not_exist_once_an_object_storage_is_configured(
    client, s3_storages
):
    assert _post(client).status_code == 404


def test_create_local_upload_only_accepts_post(client):
    assert client.get(reverse("create_local_upload", args=["public"])).status_code == 405


def test_create_local_upload_does_not_know_an_unknown_storage(client):
    assert _post(client, storage_alias="nope").status_code == 404
