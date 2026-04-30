import pytest


@pytest.fixture
def valid_mentor_data():
    return {
        "first_name": "Marie",
        "last_name": "Dupont",
        "email": "marie.dupont@example.com",
        "phone": "0612345678",
        "professional_situation": "Ingénieure logiciel",
        "structure_name": "Tech Corp",
        "job_title": "Développeuse backend",
        "postal_code": "75011",
    }
