from datetime import timedelta

from django.conf import settings
from django.core.files.storage import storages
from django.utils import timezone
from storages.backends.s3 import S3Storage

from techpourtoutes.forms.event.details_form import IMAGE_PREFIX as EVENT_IMAGE_PREFIX
from techpourtoutes.models import Event, MakeuseProject
from techpourtoutes.models.makeuse_project import IMAGE_PREFIX as MAKEUSE_PROJECT_IMAGE_PREFIX

from ..base import BaseService

# Longer than any form stays open: an image is uploaded as soon as it is picked, and held by
# nothing until the form is saved.
GRACE_PERIOD = timedelta(days=1)

# Each prefix the browser uploads images to, and the model whose `image` column holds them.
IMAGE_HOLDERS = {
    EVENT_IMAGE_PREFIX: Event,
    MAKEUSE_PROJECT_IMAGE_PREFIX: MakeuseProject,
}


class PurgeOrphanImages(BaseService):
    """Deletes the uploaded images nothing holds: picked in a form that was abandoned, replaced
    by another one, or left behind by a deleted record.

    It compares a bucket with a database, so both have to be the same app's: from a laptop that
    holds staging's keys, it would find every image of staging an orphan of the local database.
    """

    def perform(self, *, grace_period=GRACE_PERIOD):
        storage = storages["public"]
        if isinstance(storage, S3Storage) and not settings.APP_NAME:
            self.fail("Réservé à l'app propriétaire du bucket : ses images sont dans sa base.")
        uploaded_before = timezone.now() - grace_period
        orphans = [
            name
            for prefix, model in IMAGE_HOLDERS.items()
            for name in _orphans(storage, prefix, model, uploaded_before=uploaded_before)
        ]
        for name in orphans:
            storage.delete(name)
        self.deleted = len(orphans)


def _orphans(storage, prefix, model, *, uploaded_before):
    held = set(model.objects.exclude(image="").values_list("image", flat=True))
    return [
        name
        for name in _stored_images(storage, prefix)
        if name not in held and storage.get_modified_time(name) < uploaded_before
    ]


def _stored_images(storage, prefix):
    """A bucket lists an empty prefix as empty; the disk has no such directory."""
    try:
        _, files = storage.listdir(prefix)
    except FileNotFoundError:
        return []
    return [f"{prefix}/{name}" for name in files]
