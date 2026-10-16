import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from techpourtoutes.models import MakeuseProject
from techpourtoutes.tests.models.test_makeuse_project import build_makeuse_project

CHANGELIST = "admin:techpourtoutes_makeuseproject_changelist"
ADD = "admin:techpourtoutes_makeuseproject_add"


@pytest.mark.django_db
def test_makeuse_project_changelist_lists_the_projects(verified_admin_client):
    build_makeuse_project().save()

    content = verified_admin_client.get(reverse(CHANGELIST)).content.decode()

    assert "Une appli pour trouver un stage" in content
    assert "Hedy Lamarr" in content


@pytest.mark.django_db
def test_makeuse_project_add_form_uploads_the_image_to_the_public_bucket(
    verified_admin_client, s3_storages
):
    response = verified_admin_client.post(
        reverse(ADD),
        {
            "title": "Une appli pour trouver un stage",
            "project_type": "Application mobile",
            "creator_name": "Hedy Lamarr",
            "contact_email": "hedy@example.com",
            "idea": "Rapprocher les lycéennes des entreprises du quartier.",
            "background": "Terminale STI2D à Amiens.",
            "methodology": "Des entretiens, puis un prototype Figma.",
            "hobbies": "Le volley et le dessin.",
            "demo_url": "https://example.com/demo",
            "image": SimpleUploadedFile("visuel.webp", b"webp", content_type="image/webp"),
        },
    )

    assert response.status_code == 302
    project = MakeuseProject.objects.get()
    assert project.demo_url == "https://example.com/demo"
    stored = s3_storages.get_object(Bucket="tpt-test-public", Key=project.image.name)
    assert stored["Body"].read() == b"webp"
