from techpourtoutes.utils import object_storage

S3 = "storages.backends.s3.S3Storage"
FILE_SYSTEM = "django.core.files.storage.FileSystemStorage"

CONNECTION = {
    "endpoint_url": "https://s3.gra.example.net",
    "region_name": "gra",
    "access_key": "access",
    "secret_key": "secret",
    "location": "",
}
PRIVATE_URL_TTL = 120


def test_settings_dictionary_falls_back_to_the_file_system_without_a_bucket():
    storages = object_storage.settings_dictionary(
        private_bucket="",
        public_bucket="",
        public_object_acl="",
        private_url_ttl=PRIVATE_URL_TTL,
        **CONNECTION,
    )

    assert storages == {
        "default": {"BACKEND": FILE_SYSTEM},
        "public": {"BACKEND": FILE_SYSTEM},
    }


def test_settings_dictionary_signs_every_private_url_and_leaves_objects_private():
    storages = object_storage.settings_dictionary(
        private_bucket="tpt-private",
        public_bucket="tpt-public",
        public_object_acl="public-read",
        private_url_ttl=PRIVATE_URL_TTL,
        **CONNECTION,
    )

    assert storages["default"]["BACKEND"] == S3
    assert (
        storages["default"]["OPTIONS"]
        | {
            "bucket_name": "tpt-private",
            "querystring_auth": True,
            "querystring_expire": PRIVATE_URL_TTL,
            "default_acl": None,
        }
        == storages["default"]["OPTIONS"]
    )


def test_settings_dictionary_serves_public_urls_unsigned_with_the_public_acl():
    storages = object_storage.settings_dictionary(
        private_bucket="tpt-private",
        public_bucket="tpt-public",
        public_object_acl="public-read",
        private_url_ttl=PRIVATE_URL_TTL,
        **CONNECTION,
    )

    assert storages["public"]["BACKEND"] == S3
    assert (
        storages["public"]["OPTIONS"]
        | {
            "bucket_name": "tpt-public",
            "querystring_auth": False,
            "default_acl": "public-read",
        }
        == storages["public"]["OPTIONS"]
    )


def test_settings_dictionary_shares_one_connection():
    storages = object_storage.settings_dictionary(
        private_bucket="tpt-private",
        public_bucket="tpt-public",
        public_object_acl="public-read",
        private_url_ttl=PRIVATE_URL_TTL,
        **CONNECTION,
    )

    for alias in ("default", "public"):
        options = storages[alias]["OPTIONS"]
        assert options | CONNECTION == options
        config = options["client_config"]
        assert config.signature_version == "s3v4"
        assert config.s3 == {"addressing_style": "virtual"}
        assert config.request_checksum_calculation == "when_required"


def test_settings_dictionary_lets_boto_pick_the_endpoint_when_none_is_given():
    storages = object_storage.settings_dictionary(
        private_bucket="tpt-private",
        public_bucket="tpt-public",
        public_object_acl="",
        private_url_ttl=PRIVATE_URL_TTL,
        **CONNECTION | {"endpoint_url": ""},
    )

    assert storages["default"]["OPTIONS"]["endpoint_url"] is None
    assert storages["public"]["OPTIONS"]["default_acl"] is None


def test_settings_dictionary_files_a_review_app_under_its_own_prefix():
    storages = object_storage.settings_dictionary(
        private_bucket="tpt-private",
        public_bucket="tpt-public",
        public_object_acl="public-read",
        private_url_ttl=PRIVATE_URL_TTL,
        **CONNECTION | {"location": "techpourtoutes-staging-pr320"},
    )

    assert storages["default"]["OPTIONS"]["location"] == "techpourtoutes-staging-pr320"
    assert storages["public"]["OPTIONS"]["location"] == "techpourtoutes-staging-pr320"
