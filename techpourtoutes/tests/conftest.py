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
        birth_date="1985-04-12",
        email="alice@example.com",
        phone="+33612345678",
        address="10 rue de la Paix",
        professional_situation=Mentor.ProfessionalSituation.WORKING,
        structure_name="Acme",
        job_title="CTO",
        postal_code="75001",
        city="Paris",
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
        "birth_date": "1990-06-15",
        "email": "marie.dupont@example.com",
        "phone": "0612345678",
        "address": "5 avenue Victor Hugo",
        "professional_situation": "working",
        "structure_name": "Tech Corp",
        "job_title": "Développeuse backend",
        "postal_code": "75011",
        "city": "Paris",
    }


@pytest.fixture
def valid_mentor_data(valid_mentor_model_data):
    return {**valid_mentor_model_data, "terms_accepted": True}
