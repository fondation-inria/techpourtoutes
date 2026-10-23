import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.urls import reverse

from techpourtoutes.models import MakeuseProject
from techpourtoutes.tests.models.test_makeuse_project import build_makeuse_project

CHANGELIST = "admin:techpourtoutes_makeuseproject_changelist"
ADD = "admin:techpourtoutes_makeuseproject_add"
IMAGE_UPLOAD = "admin:makeuse_project_image_upload"

KEY = "makeuse_projects/0123456789abcdef0123456789abcdef.webp"


def _add_form_data(**overrides):
    return {
        "title": "Une appli pour trouver un stage",
        "category": MakeuseProject.Category.APPS_AND_WEB,
        "project_type": "Application mobile",
        "creator_name": "Hedy Lamarr",
        "contact_email": "hedy@example.com",
        "idea": "Rapprocher les lycéennes des entreprises du quartier.",
        "background": "Terminale STI2D à Amiens.",
        "methodology": "Des entretiens, puis un prototype Figma.",
        "hobbies": "Le volley et le dessin.",
        **overrides,
    }


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.mark.django_db
def test_makeuse_project_changelist_lists_the_projects(verified_admin_client):
    build_makeuse_project().save()

    content = verified_admin_client.get(reverse(CHANGELIST)).content.decode()

    assert "Une appli pour trouver un stage" in content
    assert "Hedy Lamarr" in content


@pytest.mark.django_db
def test_makeuse_project_add_form_shows_the_image_upload(verified_admin_client):
    """The key travels in a hidden input, but the row around it must not be hidden too."""
    response = verified_admin_client.get(reverse(ADD))

    assert not response.context["adminform"].form["image"].is_hidden
    assert "data-image-file" in response.content.decode()


@pytest.mark.django_db
def test_makeuse_project_add_form_links_a_beneficiary_without_typing_her_details(
    verified_admin_client, beneficiary
):
    response = verified_admin_client.post(
        reverse(ADD),
        _add_form_data(beneficiary=beneficiary.pk, creator_name="", contact_email=""),
    )

    assert response.status_code == 302
    assert MakeuseProject.objects.get().creator_label == "Jade Petit"


@pytest.mark.django_db
def test_makeuse_project_add_form_stores_the_key_of_the_uploaded_image(
    verified_admin_client, media_root
):
    storages["public"].save(KEY, ContentFile(b"webp"))

    response = verified_admin_client.post(reverse(ADD), _add_form_data(image=KEY))

    assert response.status_code == 302
    assert MakeuseProject.objects.get().image.name == KEY


@pytest.mark.django_db
@pytest.mark.parametrize(
    "key",
    [
        "events/0123456789abcdef0123456789abcdef.webp",
        "makeuse_projects/0123456789abcdef0123456789abcdef.webp",
    ],
    ids=["another_prefix", "never_uploaded"],
)
def test_makeuse_project_add_form_refuses_a_key_the_upload_did_not_give(
    verified_admin_client, media_root, key
):
    storages["public"].save("events/0123456789abcdef0123456789abcdef.webp", ContentFile(b"e"))

    response = verified_admin_client.post(reverse(ADD), _add_form_data(image=key))

    assert response.status_code == 200
    assert "image" in response.context["adminform"].form.errors
    assert not MakeuseProject.objects.exists()


@pytest.mark.django_db
def test_makeuse_project_image_upload_signs_an_upload_to_the_public_storage(
    verified_admin_client,
):
    response = verified_admin_client.post(
        reverse(IMAGE_UPLOAD), {"content_type": "image/webp", "content_length": 1_000}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["url"].startswith(reverse("create_local_upload", args=["public"]))
    assert body["key"].startswith("makeuse_projects/")
    assert body["headers"]["Content-Type"] == "image/webp"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("content_type", "content_length"),
    [("application/pdf", 1_000), ("image/webp", 2 * 1024 * 1024 + 1)],
    ids=["not_an_image", "too_heavy"],
)
def test_makeuse_project_image_upload_refuses_what_events_refuse(
    verified_admin_client, content_type, content_length
):
    response = verified_admin_client.post(
        reverse(IMAGE_UPLOAD), {"content_type": content_type, "content_length": content_length}
    )

    assert response.status_code == 400
    assert response.json()["error"]


@pytest.mark.django_db
def test_makeuse_project_image_upload_is_reserved_to_the_admin(client):
    response = client.post(
        reverse(IMAGE_UPLOAD), {"content_type": "image/webp", "content_length": 1_000}
    )

    assert response.status_code == 302
    assert reverse("admin:login") in response.url
