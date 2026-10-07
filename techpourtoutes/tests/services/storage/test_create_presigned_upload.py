from urllib.parse import parse_qs, urlparse

import pytest
from django.urls import reverse

from techpourtoutes.services.storage.create_presigned_upload import (
    CONTENT_TYPE_REFUSED,
    TOO_LARGE,
    CreatePresignedUpload,
)
from techpourtoutes.utils.local_upload import read_local_upload_policy

IMAGES = ["image/png", "image/jpeg"]


def _upload(**overrides):
    return CreatePresignedUpload(
        **{
            "storage_alias": "public",
            "prefix": "events",
            "content_type": "image/png",
            "content_length": 1_000,
            "allowed_content_types": IMAGES,
            "max_size": 5_000_000,
        }
        | overrides
    )


def _signed_headers(result):
    return parse_qs(urlparse(result.url).query)["X-Amz-SignedHeaders"][0].split(";")


def test_create_presigned_upload_names_the_file_under_its_prefix(s3_storages):
    result = _upload()

    assert result.success
    assert result.key.startswith("events/")
    assert result.key.endswith(".png")
    assert urlparse(result.url).path == f"/{result.key}"


def test_create_presigned_upload_names_every_file_differently(s3_storages):
    assert _upload().key != _upload().key


def test_create_presigned_upload_puts_to_the_storage_bucket(s3_storages):
    assert "tpt-test-public" in _upload().url
    assert "tpt-test-private" in _upload(storage_alias="default").url


def test_create_presigned_upload_pins_the_exact_size_in_the_signature(s3_storages):
    assert "content-length" in _signed_headers(_upload(content_length=1_000))


def test_create_presigned_upload_refuses_a_file_larger_than_the_maximum(s3_storages):
    result = _upload(content_length=5_000_001)

    assert result.failure
    assert result.errors == [TOO_LARGE]


def test_create_presigned_upload_refuses_an_empty_file(s3_storages):
    assert _upload(content_length=0).errors == [TOO_LARGE]


def test_create_presigned_upload_pins_the_content_type_in_the_signature(s3_storages):
    result = _upload(content_type="image/jpeg")

    assert result.headers["Content-Type"] == "image/jpeg"
    assert "content-type" in _signed_headers(result)
    assert result.key.endswith(".jpg")


def test_create_presigned_upload_makes_a_public_file_readable_by_anyone(s3_storages):
    result = _upload()

    assert result.headers["x-amz-acl"] == "public-read"
    assert "x-amz-acl" in _signed_headers(result)


def test_create_presigned_upload_leaves_a_private_file_private(s3_storages):
    result = _upload(storage_alias="default")

    assert "x-amz-acl" not in result.headers
    assert "x-amz-acl" not in _signed_headers(result)


def test_create_presigned_upload_pins_the_cache_control_of_a_public_file(s3_storages):
    result = _upload()

    assert result.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    assert "cache-control" in _signed_headers(result)


def test_create_presigned_upload_sets_no_cache_control_on_a_private_file(s3_storages):
    result = _upload(storage_alias="default")

    assert "Cache-Control" not in result.headers


def test_create_presigned_upload_refuses_a_content_type_not_allowed(s3_storages):
    result = _upload(content_type="text/html")

    assert result.failure
    assert result.errors == [CONTENT_TYPE_REFUSED]


@pytest.mark.parametrize("s3_location", ["techpourtoutes-staging-pr320"])
def test_create_presigned_upload_puts_under_the_review_app_prefix(s3_storages):
    result = _upload()

    assert result.key.startswith("events/")
    assert urlparse(result.url).path == f"/techpourtoutes-staging-pr320/{result.key}"


@pytest.mark.parametrize("storage_alias", ["default", "public"])
def test_create_presigned_upload_puts_to_the_app_without_an_object_storage(storage_alias):
    result = _upload(storage_alias=storage_alias, content_length=1_000)

    assert result.success
    url = urlparse(result.url)
    assert url.path == reverse("create_local_upload", args=[storage_alias])
    assert result.headers == {"Content-Type": "image/png"}
    assert read_local_upload_policy(parse_qs(url.query)["policy"][0]) == {
        "storage_alias": storage_alias,
        "key": result.key,
        "content_type": "image/png",
        "content_length": 1_000,
    }


def test_create_presigned_upload_refuses_a_content_type_not_allowed_without_an_object_storage():
    assert _upload(content_type="text/html").failure


def test_create_presigned_upload_refuses_a_file_too_large_without_an_object_storage():
    assert _upload(content_length=5_000_001).errors == [TOO_LARGE]
