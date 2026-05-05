import pytest


@pytest.fixture
def mentor(db):
    from techpourtoutes.models import Mentor

    m = Mentor(
        username="alice@example.com",
        first_name="Alice",
        last_name="Martin",
        email="alice@example.com",
        phone="+33612345678",
        professional_situation=Mentor.ProfessionalSituation.WORKING,
        structure_name="Acme",
        job_title="CTO",
        postal_code="75001",
    )
    m.save()
    return m
