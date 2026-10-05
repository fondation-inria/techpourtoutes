from uuid import uuid4

import httpx
from botocore.exceptions import BotoCoreError, ClientError
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError
from storages.backends.s3 import S3Storage

from techpourtoutes.services.storage.create_presigned_upload import CreatePresignedUpload

PROBE = b"ok"
PREFIX = "check_object_storage"
ANONYMOUS_READ_STATUS = {"default": 403, "public": 200}


class Command(BaseCommand):
    help = (
        "Vérifier l'object storage : écriture, lecture, droits d'accès anonymes et upload "
        "pré-signé, sur le stockage privé puis public."
    )

    def handle(self, *args, **options):
        for alias in ANONYMOUS_READ_STATUS:
            try:
                self._check(alias)
            except (BotoCoreError, ClientError, httpx.HTTPError) as error:
                raise CommandError(f"  {alias} : {error}") from error

    def _check(self, alias):
        storage = storages[alias]
        if not isinstance(storage, S3Storage):
            raise CommandError("  Aucun object storage n'est configuré (S3_PRIVATE_BUCKET).")
        name = storage.save(f"{PREFIX}/{uuid4().hex}.txt", ContentFile(PROBE))
        try:
            self._check_read(alias, storage.url(name))
        finally:
            storage.delete(name)
        self._check_presigned_upload(alias, storage)
        self.stdout.write(self.style.SUCCESS(f"  {alias} ({storage.bucket_name}) : OK"))

    def _check_read(self, alias, url):
        if not httpx.get(url).is_success:
            raise CommandError(f"  {alias} : lecture refusée par l'URL que génère l'application.")
        anonymous_status = httpx.get(url.split("?")[0]).status_code
        if anonymous_status != ANONYMOUS_READ_STATUS[alias]:
            raise CommandError(
                f"  {alias} : lecture anonyme en {anonymous_status}, "
                f"{ANONYMOUS_READ_STATUS[alias]} attendu."
            )

    def _check_presigned_upload(self, alias, storage):
        upload = CreatePresignedUpload(
            storage_alias=alias,
            prefix=PREFIX,
            content_type="text/plain",
            content_length=len(PROBE),
            allowed_content_types=["text/plain"],
            max_size=len(PROBE),
        )
        try:
            if self._put(upload, PROBE * 2).is_success:
                raise CommandError(f"  {alias} : un fichier trop lourd a été accepté.")
            if not self._put(upload, PROBE).is_success:
                raise CommandError(f"  {alias} : l'upload pré-signé a été refusé.")
        finally:
            storage.delete(upload.key)

    def _put(self, upload, content):
        return httpx.put(upload.url, content=content, headers=upload.headers)
