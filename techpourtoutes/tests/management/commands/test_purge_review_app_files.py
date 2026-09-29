import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

PREFIX = "techpourtoutes-staging-pr320"


def _keys(client, bucket):
    return [item["Key"] for item in client.list_objects_v2(Bucket=bucket).get("Contents", [])]


@pytest.mark.parametrize("s3_location", [PREFIX])
def test_purge_review_app_files_deletes_every_file_under_the_review_app_prefix(
    s3_storages, capsys
):
    for bucket in ("tpt-test-private", "tpt-test-public"):
        s3_storages.put_object(Bucket=bucket, Key=f"{PREFIX}/events/a.png", Body=b"a")
        s3_storages.put_object(Bucket=bucket, Key=f"{PREFIX}/events/b.png", Body=b"b")

    call_command("purge_review_app_files")

    assert _keys(s3_storages, "tpt-test-private") == []
    assert _keys(s3_storages, "tpt-test-public") == []
    assert "default : 2 fichier(s) supprimé(s)" in capsys.readouterr().out


@pytest.mark.parametrize("s3_location", [PREFIX])
def test_purge_review_app_files_spares_staging_and_other_review_apps(s3_storages):
    kept = ["events/staging.png", f"{PREFIX}0/events/other.png"]
    for key in kept:
        s3_storages.put_object(Bucket="tpt-test-private", Key=key, Body=b"x")

    call_command("purge_review_app_files")

    assert sorted(_keys(s3_storages, "tpt-test-private")) == sorted(kept)


def test_purge_review_app_files_refuses_to_run_outside_a_review_app(s3_storages):
    s3_storages.put_object(Bucket="tpt-test-private", Key="events/staging.png", Body=b"x")

    with pytest.raises(CommandError, match="review app"):
        call_command("purge_review_app_files")

    assert _keys(s3_storages, "tpt-test-private") == ["events/staging.png"]


def test_purge_review_app_files_refuses_to_run_without_an_object_storage():
    with pytest.raises(CommandError, match="review app"):
        call_command("purge_review_app_files")
