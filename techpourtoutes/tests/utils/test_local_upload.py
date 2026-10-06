import time
from unittest.mock import patch

import pytest
from django.core import signing

from techpourtoutes.utils.local_upload import read_local_upload_policy, sign_local_upload_policy


def _sign():
    return sign_local_upload_policy(
        storage_alias="public",
        key="events/abc.png",
        content_type="image/png",
        content_length=1_000,
    )


def test_read_local_upload_policy_returns_what_was_signed():
    assert read_local_upload_policy(_sign()) == {
        "storage_alias": "public",
        "key": "events/abc.png",
        "content_type": "image/png",
        "content_length": 1_000,
    }


def test_read_local_upload_policy_refuses_a_tampered_policy():
    with pytest.raises(signing.BadSignature):
        read_local_upload_policy(_sign()[:-1] + "x")


def test_read_local_upload_policy_refuses_an_expired_policy():
    policy = _sign()

    with patch("django.core.signing.time.time", return_value=time.time() + 601):
        with pytest.raises(signing.SignatureExpired):
            read_local_upload_policy(policy)
