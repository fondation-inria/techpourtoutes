import mimetypes
import posixpath
from urllib.parse import urlencode
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import storages
from django.urls import reverse
from storages.backends.s3 import S3Storage

from techpourtoutes.utils.local_upload import sign_local_upload_policy

from ..base import BaseService

CONTENT_TYPE_REFUSED = "Ce type de fichier n'est pas accepté."
TOO_LARGE = "Ce fichier dépasse la taille autorisée."


class CreatePresignedUpload(BaseService):
    """Signs a PUT the browser sends straight to the bucket, so the file never goes through
    the app.

    The signature covers the headers the browser must send — content type, ACL — and
    the exact size, checked against `max_size` here: the bucket refuses an upload that breaks
    any of them before storing a single byte. The key is chosen here, from a UUID and the
    content type: nothing the client names ends up in it. `result.key` is the name the storage
    knows the file by; the URL may prefix it with the storage's `location`.

    A PUT rather than a POST form: OVH only checks a POST policy against credentials it
    happens to have cached, and refuses it as forged after a while without traffic.

    Without an object storage — local dev, offline — the PUT goes to `create_local_upload`
    instead, which enforces the same signature and writes to the disk: the browser cannot tell.
    """

    def perform(
        self,
        *,
        storage_alias,
        prefix,
        content_type,
        content_length,
        allowed_content_types,
        max_size,
    ):
        if content_type not in allowed_content_types:
            self.fail(CONTENT_TYPE_REFUSED)
        if not 1 <= content_length <= max_size:
            self.fail(TOO_LARGE)
        self.key = _new_key(prefix, content_type)
        storage = storages[storage_alias]
        if isinstance(storage, S3Storage):
            self._sign_for_the_bucket(storage, content_type, content_length)
        else:
            self._sign_for_the_app(storage_alias, content_type, content_length)

    def _sign_for_the_bucket(self, storage, content_type, content_length):
        self.headers = _headers_sent_with_the_file(storage, content_type)
        self.url = storage.connection.meta.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": storage.bucket_name,
                "Key": posixpath.join(storage.location, self.key),
                "ContentLength": content_length,
                **_as_put_object_params(self.headers),
            },
            ExpiresIn=settings.S3_UPLOAD_URL_TTL,
        )

    def _sign_for_the_app(self, storage_alias, content_type, content_length):
        self.headers = {"Content-Type": content_type}
        policy = sign_local_upload_policy(
            storage_alias=storage_alias,
            key=self.key,
            content_type=content_type,
            content_length=content_length,
        )
        self.url = (
            f"{reverse('create_local_upload', args=[storage_alias])}?"
            f"{urlencode({'policy': policy})}"
        )


def _new_key(prefix, content_type):
    return f"{prefix}/{uuid4().hex}{mimetypes.guess_extension(content_type)}"


def _headers_sent_with_the_file(storage, content_type):
    """The content type, and the ACL a public file needs to be readable by anyone."""
    acl = {"x-amz-acl": storage.default_acl} if storage.default_acl else {}
    return {"Content-Type": content_type} | acl


_PUT_OBJECT_PARAMS = {"Content-Type": "ContentType", "x-amz-acl": "ACL"}


def _as_put_object_params(headers):
    """A header is only enforced by the bucket if it is signed: otherwise the browser could
    send any value in its place."""
    return {_PUT_OBJECT_PARAMS[name]: value for name, value in headers.items()}
