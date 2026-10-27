from unittest.mock import patch

import pytest

from techpourtoutes.tasks.send_legal_representative_authorization_proof import (
    send_legal_representative_authorization_proof_task,
)


@pytest.mark.django_db
def test_task_loads_the_authorization_and_sends_its_proof(authorization):
    with patch(
        "techpourtoutes.tasks.send_legal_representative_authorization_proof."
        "SendLegalRepresentativeAuthorizationProof"
    ) as MockSendProof:
        send_legal_representative_authorization_proof_task(authorization_pk=str(authorization.pk))

    MockSendProof.assert_called_once_with(authorization=authorization)
