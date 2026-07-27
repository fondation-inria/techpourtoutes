from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def pro(db):
    from techpourtoutes.models import Pro

    pro = Pro(
        username="alice@example.com",
        civility=Pro.Civility.MADAME,
        first_name="Alice",
        last_name="Martin",
        email="alice@example.com",
        phone="+33612345678",
        postal_code="75001",
        professional_situation=Pro.ProfessionalSituation.WORKING,
        job_title="Chercheuse",
        structure_name="Inria",
        brevo_sync_enabled=True,
    )
    pro.save()
    return pro


@pytest.fixture
def higher_ed_school(db):
    from techpourtoutes.models import HigherEdSchool

    school = HigherEdSchool(
        full_name="Université Paris-Saclay",
        name="UPSaclay",
        siret="13002602400054",
        uai="0911101X",
    )
    school.save()
    return school


@pytest.fixture
def school(db):
    from techpourtoutes.models import School

    school = School(identifier="0750001A", name="Lycée Voltaire", postal_code="75011")
    school.save()
    return school


@pytest.fixture
def beneficiary(db):
    from datetime import date

    from techpourtoutes.models import Beneficiary

    beneficiary = Beneficiary(
        username="jade@example.com",
        first_name="Jade",
        last_name="Petit",
        email="jade@example.com",
        phone="+33612345678",
        birth_date=date(2008, 3, 15),
    )
    beneficiary.save()
    return beneficiary


@pytest.fixture
def experience(pro, higher_ed_school):
    from datetime import date

    from techpourtoutes.models import TrainingExperience

    return TrainingExperience.objects.create(
        user=pro,
        higher_ed_school=higher_ed_school,
        level=TrainingExperience.Level.BAC_3,
        start_date=date(2019, 9, 1),
        end_date=date(2020, 8, 31),
        course="Master Informatique",
    )


@pytest.fixture
def beneficiary_experience(beneficiary, school):
    from datetime import date

    from techpourtoutes.models import TrainingExperience

    return TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.TERMINALE,
        start_date=date(2023, 9, 1),
        end_date=date(2024, 8, 31),
        course="Spécialité mathématiques",
    )


@pytest.fixture
def mock_create_mentor():
    instance = MagicMock(success=True, failure=False, errors=[])
    with patch(
        "techpourtoutes.views.coalition_views.CreateMentor",
        return_value=instance,
    ) as mock:
        yield mock


@pytest.fixture
def valid_pro_model_data():
    return {
        "civility": "Madame",
        "first_name": "Marie",
        "last_name": "Dupont",
        "email": "marie.dupont@example.com",
        "phone": "0612345678",
        "postal_code": "75011",
        "professional_situation": "working",
        "job_title": "Développeuse backend",
        "structure_name": "Grande entreprise",
    }


@pytest.fixture
def valid_pro_data(valid_pro_model_data):
    return {**valid_pro_model_data, "terms_accepted": True, "manifeste_accepted": True}


@pytest.fixture
def inactive_user(db):
    from techpourtoutes.models import User

    user = User.objects.create_user(
        username="inactive@example.com", email="inactive@example.com", is_active=False
    )
    return user
