from django.conf import settings
from django.core import signing

SALT = "techpourtoutes.local_upload"


def sign_local_upload_policy(
    *, storage_alias: str, key: str, content_type: str, content_length: int
) -> str:
    """What a presigned PUT pins, signed by the app for the upload it receives itself when no
    object storage is configured."""
    return signing.dumps(
        {
            "storage_alias": storage_alias,
            "key": key,
            "content_type": content_type,
            "content_length": content_length,
        },
        salt=SALT,
    )


def read_local_upload_policy(policy: str) -> dict:
    """Raises `signing.BadSignature` — `SignatureExpired` included — like a bucket refusing it."""
    return signing.loads(policy, salt=SALT, max_age=settings.S3_UPLOAD_URL_TTL)
