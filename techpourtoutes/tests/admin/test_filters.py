import pytest
from django.urls import reverse

CHANGELIST = "admin:techpourtoutes_pro_changelist"


@pytest.mark.django_db
def test_changelist_engagement_filter_single(verified_admin_client, pros):
    content = verified_admin_client.get(
        reverse(CHANGELIST), {"engagement": "mentor"}
    ).content.decode()
    assert "emma@example.com" in content
    assert "bob@example.com" not in content
    assert "carol@example.com" not in content


@pytest.mark.django_db
def test_changelist_engagement_filter_multiple(verified_admin_client, pros):
    content = verified_admin_client.get(
        reverse(CHANGELIST), {"engagement": "mentor,sponsor"}
    ).content.decode()
    # Union of both engagements; the unrelated ambassador is excluded.
    assert "emma@example.com" in content
    assert "bob@example.com" in content
    assert "carol@example.com" not in content
