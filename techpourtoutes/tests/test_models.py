import uuid

import pytest
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_user_has_uuid_pk():
    from techpourtoutes.models import User

    user = User.objects.create_user(username="test@example.com", email="test@example.com")
    assert isinstance(user.pk, uuid.UUID)


@pytest.mark.django_db
def test_mentor_inherits_user():
    from techpourtoutes.models import Mentor, User

    assert issubclass(Mentor, User)


@pytest.mark.django_db
def test_mentor_save_sets_unusable_password(valid_mentor_model_data):
    from techpourtoutes.models import Mentor

    mentor = Mentor(username="marie.dupont@example.com", **valid_mentor_model_data)
    mentor.save()
    assert not mentor.has_usable_password()


@pytest.mark.django_db
def test_mentor_creation_saves_all_fields(valid_mentor_model_data):
    from techpourtoutes.models import Mentor

    Mentor(username="marie.dupont@example.com", **valid_mentor_model_data).save()

    saved = Mentor.objects.get(email="marie.dupont@example.com")
    assert saved.civility == "Madame"
    assert saved.first_name == "Marie"
    assert saved.last_name == "Dupont"
    assert saved.email == "marie.dupont@example.com"
    assert saved.birth_date.isoformat() == "1990-06-15"
    assert saved.phone.national_number == 612345678
    assert saved.professional_situation == "working"
    assert saved.address == "5 avenue Parmentier"
    assert saved.postal_code == "75011"
    assert saved.city == "Paris"
    assert saved.job_title == "Développeuse backend"
    assert saved.structure_name == "Grande entreprise"
    assert saved.structure_address == "25 avenue de la République"
    assert saved.structure_postal_code == "75011"
    assert saved.structure_city == "Paris"


@pytest.mark.django_db
def test_mentor_structure_name_optional(valid_mentor_model_data):
    from techpourtoutes.models import Mentor

    data = {**valid_mentor_model_data, "email": "autre@example.com", "structure_name": ""}
    Mentor(username="autre@example.com", **data).save()
    assert Mentor.objects.filter(email="autre@example.com").exists()


@pytest.mark.django_db
def test_mentor_save_raises_if_invalid(valid_mentor_model_data):
    from techpourtoutes.models import Mentor

    data = {**valid_mentor_model_data, "email": "not-an-email"}
    mentor = Mentor(username="bad@example.com", **data)
    with pytest.raises(ValidationError):
        mentor.save()


@pytest.mark.django_db
def test_mentor_invalid_structure_postal_code_raises(valid_mentor_model_data):
    from techpourtoutes.models import Mentor

    data = {**valid_mentor_model_data, "structure_postal_code": "abc"}
    mentor = Mentor(username="marie.dupont@example.com", **data)
    with pytest.raises(ValidationError):
        mentor.save()
