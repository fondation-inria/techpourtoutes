import pytest
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_school_str_shows_name_and_postal_code():
    from techpourtoutes.models import School

    school = School(identifier="0750001A", name="Lycée Voltaire", postal_code="75011")
    school.save()
    assert str(school) == "Lycée Voltaire (75011)"


@pytest.mark.django_db
def test_school_identifier_is_unique():
    from techpourtoutes.models import School

    School(identifier="0750001A", name="Lycée Voltaire", postal_code="75011").save()
    with pytest.raises(ValidationError):
        School(identifier="0750001A", name="Autre lycée", postal_code="75012").save()


@pytest.mark.django_db
def test_school_save_populates_normalized_name():
    from techpourtoutes.models import School

    school = School(identifier="0750001A", name="Lycée Privée", postal_code="75001")
    school.save()
    assert school.name_normalized == "Lycee Privee"
