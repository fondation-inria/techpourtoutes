from botocore.config import Config

S3 = "storages.backends.s3.S3Storage"
FILE_SYSTEM = "django.core.files.storage.FileSystemStorage"


def settings_dictionary(
    *,
    private_bucket: str,
    public_bucket: str,
    public_object_acl: str,
    private_url_ttl: int,
    endpoint_url: str,
    region_name: str,
    access_key: str,
    secret_key: str,
    location: str,
) -> dict:
    """The `default` (private) and `public` entries of `STORAGES`, for any S3-compatible provider.

    Without a bucket — local dev, tests — both fall back to the file system. A non-empty
    `location` prefixes every key, so that a review app's files can be purged with it.
    """
    if not private_bucket:
        return {"default": {"BACKEND": FILE_SYSTEM}, "public": {"BACKEND": FILE_SYSTEM}}

    connection = {
        "endpoint_url": endpoint_url or None,
        "region_name": region_name,
        "access_key": access_key,
        "secret_key": secret_key,
        "location": location,
        "client_config": Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    }
    return {
        "default": {
            "BACKEND": S3,
            "OPTIONS": connection
            | {
                "bucket_name": private_bucket,
                "querystring_auth": True,
                "querystring_expire": private_url_ttl,
                "default_acl": None,
            },
        },
        "public": {
            "BACKEND": S3,
            "OPTIONS": connection
            | {
                "bucket_name": public_bucket,
                "querystring_auth": False,
                "default_acl": public_object_acl or None,
            },
        },
    }
