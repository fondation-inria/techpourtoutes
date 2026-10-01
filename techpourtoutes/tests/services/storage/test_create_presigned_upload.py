import base64
import json

import pytest
from django.urls import reverse

from techpourtoutes.services.storage.create_presigned_upload import CreatePresignedUpload
from techpourtoutes.utils.local_upload import read_local_upload_policy

IMAGES = ["image/png", "image/jpeg"]


def _upload(**overrides):
    return CreatePresignedUpload(
        **{
            "storage_alias": "public",
            "prefix": "events",
            "content_type": "image/png",
            "allowed_content_types": IMAGES,
            "max_size": 5_000_000,
        }
        | overrides
    )


def _policy_conditions(result):
    return json.loads(base64.b64decode(result.fields["policy"]))["conditions"]


def test_create_presigned_upload_names_the_file_under_its_prefix(s3_storages):
    result = _upload()

    assert result.success
    assert result.key.startswith("events/")
    assert result.key.endswith(".png")
    assert result.fields["key"] == result.key


def test_create_presigned_upload_names_every_file_differently(s3_storages):
    assert _upload().key != _upload().key


def test_create_presigned_upload_posts_to_the_storage_bucket(s3_storages):
    assert "tpt-test-public" in _upload().url
    assert "tpt-test-private" in _upload(storage_alias="default").url


def test_create_presigned_upload_bounds_the_size_in_the_signed_policy(s3_storages):
    result = _upload(max_size=1_000)

    assert ["content-length-range", 1, 1_000] in _policy_conditions(result)


def test_create_presigned_upload_pins_the_content_type_in_the_signed_policy(s3_storages):
    result = _upload(content_type="image/jpeg")

    assert result.fields["Content-Type"] == "image/jpeg"
    assert {"Content-Type": "image/jpeg"} in _policy_conditions(result)
    assert result.key.endswith(".jpg")


def test_create_presigned_upload_makes_a_public_file_readable_by_anyone(s3_storages):
    result = _upload()

    assert result.fields["acl"] == "public-read"
    assert {"acl": "public-read"} in _policy_conditions(result)


def test_create_presigned_upload_leaves_a_private_file_private(s3_storages):
    result = _upload(storage_alias="default")

    assert "acl" not in result.fields
    assert not any("acl" in condition for condition in _policy_conditions(result))


def test_create_presigned_upload_pins_the_cache_control_of_a_public_file(s3_storages):
    result = _upload()

    assert result.fields["Cache-Control"] == "public, max-age=31536000, immutable"
    assert {"Cache-Control": "public, max-age=31536000, immutable"} in _policy_conditions(result)


def test_create_presigned_upload_sets_no_cache_control_on_a_private_file(s3_storages):
    result = _upload(storage_alias="default")

    assert "Cache-Control" not in result.fields


def test_create_presigned_upload_refuses_a_content_type_not_allowed(s3_storages):
    result = _upload(content_type="text/html")

    assert result.failure
    assert result.errors == ["Ce type de fichier n'est pas accepté."]


@pytest.mark.parametrize("s3_location", ["techpourtoutes-staging-pr320"])
def test_create_presigned_upload_posts_under_the_review_app_prefix(s3_storages):
    result = _upload()

    assert result.key.startswith("events/")
    assert result.fields["key"] == f"techpourtoutes-staging-pr320/{result.key}"


@pytest.mark.parametrize("storage_alias", ["default", "public"])
def test_create_presigned_upload_posts_to_the_app_without_an_object_storage(storage_alias):
    result = _upload(storage_alias=storage_alias, max_size=1_000)

    assert result.success
    assert result.url == reverse("create_local_upload", args=[storage_alias])
    assert result.fields["key"] == result.key
    assert read_local_upload_policy(result.fields["policy"]) == {
        "storage_alias": storage_alias,
        "key": result.key,
        "content_type": "image/png",
        "max_size": 1_000,
    }


def test_create_presigned_upload_refuses_a_content_type_not_allowed_without_an_object_storage():
    assert _upload(content_type="text/html").failure
