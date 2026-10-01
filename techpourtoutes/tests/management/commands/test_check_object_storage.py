import httpx
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from techpourtoutes.management.commands.check_object_storage import PROBE


@pytest.fixture
def bucket_over_http(httpx_mock):
    """What the buckets answer a browser: moto only stands in for boto3, not for plain HTTP."""

    def register(*, enforces_size=True, private_readable=False):
        def respond(request):
            if request.method == "POST":
                oversized = PROBE * 2 in request.content
                return httpx.Response(400 if oversized and enforces_size else 204)
            signed = "X-Amz-Signature" in request.url.params
            public = request.url.host.startswith("tpt-test-public")
            return httpx.Response(200 if signed or public or private_readable else 403)

        httpx_mock.add_callback(respond, is_reusable=True)

    return register


def test_check_object_storage_reports_both_storages_and_leaves_nothing_behind(
    s3_storages, bucket_over_http, capsys
):
    bucket_over_http()

    call_command("check_object_storage")

    output = capsys.readouterr().out
    assert "default (tpt-test-private) : OK" in output
    assert "public (tpt-test-public) : OK" in output
    for bucket in ("tpt-test-private", "tpt-test-public"):
        assert s3_storages.list_objects_v2(Bucket=bucket)["KeyCount"] == 0


def test_check_object_storage_fails_without_an_object_storage():
    with pytest.raises(CommandError, match="Aucun object storage n'est configuré"):
        call_command("check_object_storage")


def test_check_object_storage_fails_when_a_bucket_is_missing(s3_storages):
    s3_storages.delete_bucket(Bucket="tpt-test-private")

    with pytest.raises(CommandError, match="default"):
        call_command("check_object_storage")


def test_check_object_storage_fails_when_the_bucket_accepts_an_oversized_upload(
    s3_storages, bucket_over_http
):
    bucket_over_http(enforces_size=False)

    with pytest.raises(CommandError, match="fichier trop lourd"):
        call_command("check_object_storage")


def test_check_object_storage_fails_when_a_private_file_is_readable_by_anyone(
    s3_storages, bucket_over_http
):
    bucket_over_http(private_readable=True)

    with pytest.raises(CommandError, match="lecture anonyme"):
        call_command("check_object_storage")
