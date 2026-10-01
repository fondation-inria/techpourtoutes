import os
import time
from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import storages

from techpourtoutes.services.event.purge_orphan_event_images import PurgeOrphanEventImages

TWO_DAYS = 2 * 24 * 3600


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _stored(name, *, age=TWO_DAYS):
    storage = storages["public"]
    name = storage.save(name, ContentFile(b"img"))
    then = time.time() - age
    os.utime(storage.path(name), (then, then))
    return name


@pytest.mark.django_db
def test_purge_orphan_event_images_deletes_an_old_image_no_event_holds():
    orphan = _stored("events/orphan.png")

    result = PurgeOrphanEventImages()

    assert result.success
    assert result.deleted == 1
    assert not storages["public"].exists(orphan)


@pytest.mark.django_db
def test_purge_orphan_event_images_keeps_the_image_of_an_event(event):
    event.image = _stored("events/held.png")
    event.save()

    PurgeOrphanEventImages()

    assert storages["public"].exists(event.image.name)


@pytest.mark.django_db
def test_purge_orphan_event_images_keeps_an_image_still_in_its_funnel():
    """Uploaded minutes ago: the pro has not reached the last screen yet."""
    recent = _stored("events/recent.png", age=60)

    PurgeOrphanEventImages()

    assert storages["public"].exists(recent)


@pytest.mark.django_db
def test_purge_orphan_event_images_leaves_other_files_alone():
    other = _stored("avatars/someone.png")

    PurgeOrphanEventImages()

    assert storages["public"].exists(other)


@pytest.mark.django_db
def test_purge_orphan_event_images_refuses_a_bucket_outside_its_own_app(s3_storages, settings):
    """Run from a laptop holding staging's keys, it would compare staging's bucket with the
    laptop's database — and delete every image of staging."""
    settings.APP_NAME = ""
    s3_storages.put_object(Bucket="tpt-test-public", Key="events/staging.png", Body=b"x")

    result = PurgeOrphanEventImages()

    assert result.failure
    assert storages["public"].exists("events/staging.png")


@pytest.mark.django_db
def test_purge_orphan_event_images_purges_the_bucket_of_its_own_app(s3_storages, settings):
    settings.APP_NAME = "techpourtoutes-staging"
    s3_storages.put_object(Bucket="tpt-test-public", Key="events/orphan.png", Body=b"x")

    result = PurgeOrphanEventImages(grace_period=timedelta(0))

    assert result.success
    assert not storages["public"].exists("events/orphan.png")
