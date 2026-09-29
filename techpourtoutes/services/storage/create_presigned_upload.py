import mimetypes
import posixpath
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import storages
from django.urls import reverse
from storages.backends.s3 import S3Storage

from techpourtoutes.utils.local_upload import sign_local_upload_policy

from ..base import BaseService


class CreatePresignedUpload(BaseService):
    """Signs a form the browser posts straight to the bucket, so the file never goes through
    the app.

    The bucket enforces the signed policy — size, key, content type, ACL — and refuses an upload
    that breaks it before storing a single byte. The key is chosen here, from a UUID and the
    content type: nothing the client names ends up in it. `result.key` is the name the storage
    knows the file by; the form may prefix it with the storage's `location`.

    Without an object storage — local dev, offline — the form posts to `create_local_upload`
    instead, which enforces the same policy and writes to the disk: the browser cannot tell.
    """

    def perform(self, *, storage_alias, prefix, content_type, allowed_content_types, max_size):
        if content_type not in allowed_content_types:
            self.fail("Ce type de fichier n'est pas accepté.")
        self.key = f"{prefix}/{uuid4().hex}{mimetypes.guess_extension(content_type)}"
        storage = storages[storage_alias]
        if isinstance(storage, S3Storage):
            self._sign_for_the_bucket(storage, content_type, max_size)
        else:
            self._sign_for_the_app(storage_alias, content_type, max_size)

    def _sign_for_the_bucket(self, storage, content_type, max_size):
        acl = {"acl": storage.default_acl} if storage.default_acl else {}
        fields = {"Content-Type": content_type} | acl
        presigned = storage.connection.meta.client.generate_presigned_post(
            storage.bucket_name,
            posixpath.join(storage.location, self.key),
            Fields=fields,
            Conditions=[
                ["content-length-range", 1, max_size],
                *({name: value} for name, value in fields.items()),
            ],
            ExpiresIn=settings.S3_UPLOAD_URL_TTL,
        )
        self.url = presigned["url"]
        self.fields = presigned["fields"]

    def _sign_for_the_app(self, storage_alias, content_type, max_size):
        self.url = reverse("create_local_upload", args=[storage_alias])
        self.fields = {
            "key": self.key,
            "Content-Type": content_type,
            "policy": sign_local_upload_policy(
                storage_alias=storage_alias, key=self.key, max_size=max_size
            ),
        }
