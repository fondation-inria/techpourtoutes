from unittest.mock import patch

import pytest

from techpourtoutes.services.legal_representative_authorization.sign_authorization import (
    SignLegalRepresentativeAuthorization,
)


@pytest.fixture
def signed_authorization(authorization, settings, tmp_path):
    """Signed, its follow-up tasks left aside: the proof is yet to be built and sent."""
    settings.MEDIA_ROOT = tmp_path
    with patch(
        "techpourtoutes.services.legal_representative_authorization.sign_authorization."
        "transaction.on_commit"
    ):
        SignLegalRepresentativeAuthorization(
            authorization=authorization,
            legal_representative_name="Marie Dupont",
            relationship="mother",
            newsletter_consent=False,
            ip_address="203.0.113.7",
        )
    authorization.refresh_from_db()
    return authorization
