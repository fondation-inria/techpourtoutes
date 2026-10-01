from datetime import timedelta

from django.conf import settings
from django.core.files.storage import storages
from django.utils import timezone
from storages.backends.s3 import S3Storage

from techpourtoutes.forms.event.details_form import IMAGE_PREFIX
from techpourtoutes.models import Event

from ..base import BaseService

# Longer than any funnel stays open: an image uploaded on its details screen is held by no event
# until its last screen is posted.
GRACE_PERIOD = timedelta(days=1)


class PurgeOrphanEventImages(BaseService):
    """Deletes the event images no event holds: uploaded in a funnel that was abandoned, replaced
    by another one, or left behind by a deleted event.

    It compares a bucket with a database, so both have to be the same app's: from a laptop that
    holds staging's keys, it would find every image of staging an orphan of the local database.
    """

    def perform(self, *, grace_period=GRACE_PERIOD):
        storage = storages["public"]
        if isinstance(storage, S3Storage) and not settings.APP_NAME:
            self.fail("Réservé à l'app propriétaire du bucket : ses images sont dans sa base.")
        orphans = self._orphans(storage, uploaded_before=timezone.now() - grace_period)
        for name in orphans:
            storage.delete(name)
        self.deleted = len(orphans)

    def _orphans(self, storage, *, uploaded_before):
        held = set(Event.objects.exclude(image="").values_list("image", flat=True))
        return [
            name
            for name in _stored_images(storage)
            if name not in held and storage.get_modified_time(name) < uploaded_before
        ]


def _stored_images(storage):
    """A bucket lists an empty prefix as empty; the disk has no such directory."""
    try:
        _, files = storage.listdir(IMAGE_PREFIX)
    except FileNotFoundError:
        return []
    return [f"{IMAGE_PREFIX}/{name}" for name in files]
