import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
def test_purge_orphan_event_images_says_how_many_files_it_deleted(settings, tmp_path, capsys):
    settings.MEDIA_ROOT = tmp_path

    call_command("purge_orphan_event_images")

    assert "0 visuel(s) orphelin(s) supprimé(s)" in capsys.readouterr().out


@pytest.mark.django_db
def test_purge_orphan_event_images_fails_loudly_when_refused(s3_storages, settings):
    settings.APP_NAME = ""

    with pytest.raises(CommandError):
        call_command("purge_orphan_event_images")
