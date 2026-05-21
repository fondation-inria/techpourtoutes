from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mentor(db):
    from techpourtoutes.models import Mentor

    m = Mentor(
        username="alice@example.com",
        civility=Mentor.Civility.MADAME,
        first_name="Alice",
        last_name="Martin",
        email="alice@example.com",
        phone="+33612345678",
        postal_code="75001",
        city="Paris",
        professional_situation=Mentor.ProfessionalSituation.WORKING,
        job_title="Chercheuse",
        structure_name="Inria",
    )
    m.save()
    return m


@pytest.fixture
def mock_register_mentor_on_jobirl():
    instance = MagicMock(success=True, failure=False, errors=[], user_id=287565, token="tpt_abc")
    with patch(
        "techpourtoutes.views.coallition_views.RegisterMentorOnJobirl",
        return_value=instance,
    ) as mock:
        yield mock


@pytest.fixture
def valid_mentor_model_data():
    return {
        "civility": "Madame",
        "first_name": "Marie",
        "last_name": "Dupont",
        "email": "marie.dupont@example.com",
        "phone": "0612345678",
        "postal_code": "75011",
        "city": "Paris",
        "professional_situation": "working",
        "job_title": "Développeuse backend",
        "structure_name": "Grande entreprise",
    }


@pytest.fixture
def valid_mentor_data(valid_mentor_model_data):
    return {**valid_mentor_model_data, "terms_accepted": True}


@pytest.fixture
def inactive_user(db):
    from techpourtoutes.models import User

    user = User.objects.create_user(
        username="inactive@example.com", email="inactive@example.com", is_active=False
    )
    return user
