from unittest.mock import patch

import pytest


@pytest.fixture
def mock_brevo_client():
    with patch("techpourtoutes.services.brevo_api.base_service.BrevoClient") as mock:
        yield mock.return_value
