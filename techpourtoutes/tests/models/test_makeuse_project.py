import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from techpourtoutes.models import MakeuseProject


def build_makeuse_project(**overrides):
    return MakeuseProject(
        **{
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
    )


@pytest.mark.django_db
def test_makeuse_project_saves_without_image_nor_demo():
    project = build_makeuse_project()
    project.save()

    assert MakeuseProject.objects.get() == project
    assert not project.image
    assert project.demo_url == ""


@pytest.mark.django_db
def test_makeuse_project_images_of_the_same_name_get_their_own_key(s3_storages):
    first, second = build_makeuse_project(), build_makeuse_project()
    first.image.save("visuel.webp", ContentFile(b"first"))
    second.image.save("visuel.webp", ContentFile(b"second"))

    assert first.image.name != second.image.name
    assert first.image.name.startswith("makeuse_projects/")
    assert first.image.name.endswith(".webp")
    assert "visuel" not in first.image.name
    assert first.image.read() == b"first"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field",
    [
        "title",
        "category",
        "project_type",
        "creator_name",
        "contact_email",
        "idea",
        "background",
        "methodology",
        "hobbies",
    ],
)
def test_makeuse_project_requires_every_text(field):
    with pytest.raises(ValidationError) as error:
        build_makeuse_project(**{field: ""}).save()
    assert field in error.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"), [("contact_email", "pas-un-mail"), ("demo_url", "pas-un-lien")]
)
def test_makeuse_project_rejects_malformed_contact_details(field, value):
    with pytest.raises(ValidationError) as error:
        build_makeuse_project(**{field: value}).save()
    assert field in error.value.message_dict


@pytest.mark.django_db
def test_makeuse_project_slug_is_built_from_its_title():
    project = build_makeuse_project(title="Une appli pour trouver un stage")
    project.save()

    assert project.slug == "une-appli-pour-trouver-un-stage"


@pytest.mark.django_db
def test_makeuse_project_slug_suffixes_a_title_already_taken():
    build_makeuse_project(title="Mon robot").save()

    second = build_makeuse_project(title="Mon robot")
    second.save()

    assert second.slug == "mon-robot-2"


@pytest.mark.django_db
def test_makeuse_project_slug_never_moves_once_written():
    project = build_makeuse_project(title="Mon robot")
    project.save()

    project.title = "Mon robot v2"
    project.save()

    assert project.slug == "mon-robot"


@pytest.mark.django_db
def test_makeuse_project_slug_falls_back_when_the_title_slugifies_to_nothing():
    project = build_makeuse_project(title="★★★")
    project.save()

    assert project.slug == "projet"


@pytest.mark.parametrize(
    ("category", "color"),
    [
        (MakeuseProject.Category.APPS_AND_WEB, "yellow"),
        (MakeuseProject.Category.GAMES, "purple"),
        (MakeuseProject.Category.DATA_AND_AI, "green"),
        (MakeuseProject.Category.OBJECTS_AND_ROBOTICS, "orange"),
    ],
)
def test_makeuse_project_category_color_follows_its_category(category, color):
    assert build_makeuse_project(category=category).category_color == color
