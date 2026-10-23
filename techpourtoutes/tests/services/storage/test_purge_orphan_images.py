import os
import time
from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import storages

from techpourtoutes.services.storage.purge_orphan_images import PurgeOrphanImages
from techpourtoutes.tests.models.test_makeuse_project import build_makeuse_project

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
@pytest.mark.parametrize("prefix", ["events", "makeuse_projects"])
def test_purge_orphan_images_deletes_an_old_image_nothing_holds(prefix):
    orphan = _stored(f"{prefix}/orphan.png")

    result = PurgeOrphanImages()

    assert result.success
    assert result.deleted == 1
    assert not storages["public"].exists(orphan)


@pytest.mark.django_db
def test_purge_orphan_images_keeps_the_image_of_an_event(event):
    event.image = _stored("events/held.png")
    event.save()

    PurgeOrphanImages()

    assert storages["public"].exists(event.image.name)


@pytest.mark.django_db
def test_purge_orphan_images_keeps_the_image_of_a_makeuse_project():
    project = build_makeuse_project(image=_stored("makeuse_projects/held.png"))
    project.save()

    PurgeOrphanImages()

    assert storages["public"].exists(project.image.name)


@pytest.mark.django_db
def test_purge_orphan_images_reads_each_prefix_against_its_own_model(event):
    """An event's key filed under the projects' prefix holds nothing there."""
    event.image = _stored("events/held.png")
    event.save()
    stray = _stored("makeuse_projects/held.png")

    PurgeOrphanImages()

    assert not storages["public"].exists(stray)


@pytest.mark.django_db
def test_purge_orphan_images_keeps_an_image_still_in_its_form():
    """Uploaded minutes ago: the form it was picked in has not been saved yet."""
    recent = _stored("events/recent.png", age=60)

    PurgeOrphanImages()

    assert storages["public"].exists(recent)


@pytest.mark.django_db
def test_purge_orphan_images_leaves_other_files_alone():
    other = _stored("avatars/someone.png")

    PurgeOrphanImages()

    assert storages["public"].exists(other)


@pytest.mark.django_db
def test_purge_orphan_images_refuses_a_bucket_outside_its_own_app(s3_storages, settings):
    """Run from a laptop holding staging's keys, it would compare staging's bucket with the
    laptop's database — and delete every image of staging."""
    settings.APP_NAME = ""
    s3_storages.put_object(Bucket="tpt-test-public", Key="events/staging.png", Body=b"x")

    result = PurgeOrphanImages()

    assert result.failure
    assert storages["public"].exists("events/staging.png")


@pytest.mark.django_db
def test_purge_orphan_images_purges_the_bucket_of_its_own_app(s3_storages, settings):
    settings.APP_NAME = "techpourtoutes-staging"
    s3_storages.put_object(Bucket="tpt-test-public", Key="events/orphan.png", Body=b"x")
    s3_storages.put_object(Bucket="tpt-test-public", Key="makeuse_projects/orphan.png", Body=b"x")

    result = PurgeOrphanImages(grace_period=timedelta(0))

    assert result.success
    assert not storages["public"].exists("events/orphan.png")
    assert not storages["public"].exists("makeuse_projects/orphan.png")
