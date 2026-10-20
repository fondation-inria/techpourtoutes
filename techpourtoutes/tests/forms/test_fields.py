import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import storages

from techpourtoutes.forms.fields import EmailField, UploadedImageKeyField

KEY = "projects/0123456789abcdef0123456789abcdef.webp"


def test_email_field_lowercases_the_address():
    assert EmailField().clean("Alice@Example.COM") == "alice@example.com"


def test_email_field_leaves_an_omitted_optional_value_alone():
    assert EmailField(required=False).clean("") == ""


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def test_uploaded_image_key_field_accepts_a_key_the_upload_gave(media_root):
    storages["public"].save(KEY, ContentFile(b"webp"))

    assert UploadedImageKeyField(prefix="projects").clean(KEY) == KEY


def test_uploaded_image_key_field_accepts_no_image():
    assert UploadedImageKeyField(prefix="projects").clean("") == ""


@pytest.mark.parametrize(
    "key",
    [
        "events/0123456789abcdef0123456789abcdef.webp",
        "projects/0123456789abcdef0123456789abcdef.webp",
        "projects/visuel.webp",
    ],
    ids=["another_prefix", "never_uploaded", "not_a_signed_key"],
)
def test_uploaded_image_key_field_refuses_a_key_the_upload_did_not_give(media_root, key):
    storages["public"].save("events/0123456789abcdef0123456789abcdef.webp", ContentFile(b"e"))
    storages["public"].save("projects/visuel.webp", ContentFile(b"v"))

    with pytest.raises(ValidationError):
        UploadedImageKeyField(prefix="projects").clean(key)
