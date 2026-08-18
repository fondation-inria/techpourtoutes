import pytest
from django.urls import reverse

CHANGELIST = "admin:techpourtoutes_pro_changelist"
BENEFICIARY_CHANGELIST = "admin:techpourtoutes_beneficiary_changelist"


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


@pytest.mark.django_db
def test_changelist_mentoring_status_filter(
    verified_admin_client, beneficiaries_by_mentoring_status
):
    def emails_for(status):
        content = verified_admin_client.get(
            reverse(BENEFICIARY_CHANGELIST), {"mentoring_status": status}
        ).content.decode()
        return {name: name in content for name in ("diane", "elise", "fanny")}

    assert emails_for("not_concerned") == {"diane": True, "elise": False, "fanny": False}
    assert emails_for("pending") == {"diane": False, "elise": True, "fanny": False}
    assert emails_for("registered") == {"diane": False, "elise": False, "fanny": True}
