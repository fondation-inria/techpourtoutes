from urllib.parse import urlencode

import pytest
from django.core.files.storage import storages
from django.test import Client
from django.urls import reverse

from techpourtoutes.utils.local_upload import sign_local_upload_policy

KEY = "events/abc.png"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _url(storage_alias, policy):
    return (
        f"{reverse('create_local_upload', args=[storage_alias])}?{urlencode({'policy': policy})}"
    )


def _put(
    client,
    *,
    content=b"png",
    content_type="image/png",
    storage_alias="public",
    policy_alias="public",
):
    policy = sign_local_upload_policy(
        storage_alias=policy_alias, key=KEY, content_type="image/png", content_length=3
    )
    return client.put(_url(storage_alias, policy), content, content_type=content_type)


def test_create_local_upload_stores_the_file_under_the_signed_key(client):
    response = _put(client)

    assert response.status_code == 200
    assert storages["public"].open(KEY).read() == b"png"


def test_create_local_upload_needs_no_csrf_token_like_a_bucket():
    assert _put(Client(enforce_csrf_checks=True)).status_code == 200


def test_create_local_upload_refuses_a_file_larger_than_the_signed_size(client):
    response = _put(client, content=b"too big")

    assert response.status_code == 403
    assert not storages["public"].exists(KEY)


def test_create_local_upload_refuses_a_file_smaller_than_the_signed_size(client):
    assert _put(client, content=b"pn").status_code == 403


def test_create_local_upload_refuses_a_tampered_policy(client):
    response = client.put(_url("public", "forged"), b"png", content_type="image/png")

    assert response.status_code == 403


def test_create_local_upload_refuses_a_policy_signed_for_another_storage(client):
    assert _put(client, storage_alias="public", policy_alias="default").status_code == 403


def test_create_local_upload_refuses_a_content_type_other_than_the_signed_one(client):
    response = _put(client, content_type="text/html")

    assert response.status_code == 403
    assert not storages["public"].exists(KEY)


def test_create_local_upload_does_not_exist_once_an_object_storage_is_configured(
    client, s3_storages
):
    assert _put(client).status_code == 404


def test_create_local_upload_only_accepts_put(client):
    assert client.get(reverse("create_local_upload", args=["public"])).status_code == 405


def test_create_local_upload_does_not_know_an_unknown_storage(client):
    assert _put(client, storage_alias="nope").status_code == 404
