from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_register_mentor_on_jobirl():
    instance = MagicMock(success=True, failure=False, errors=[], user_id=287565, token="tpt_abc")
    with patch(
        "techpourtoutes.views.coallition_views.RegisterMentorOnJobirl",
        return_value=instance,
    ) as mock:
        yield mock


@pytest.fixture
def valid_mentor_data():
    return {
        "first_name": "Marie",
        "last_name": "Dupont",
        "email": "marie.dupont@example.com",
        "phone": "0612345678",
        "professional_situation": "working",
        "structure_name": "Tech Corp",
        "job_title": "Développeuse backend",
        "postal_code": "75011",
    }
