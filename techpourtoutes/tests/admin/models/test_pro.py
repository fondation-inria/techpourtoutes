import pytest
from django.urls import reverse

CHANGELIST = "admin:techpourtoutes_pro_changelist"


@pytest.mark.django_db
def test_admin_pro_hides_jobirl_token_and_locks_id(verified_admin_client, admin_pro):
    admin_pro.jobirl_user_id = 8675309
    admin_pro.jobirl_user_token = "jobirl-token-do-not-show"
    admin_pro.save()
    url = reverse("admin:techpourtoutes_pro_change", args=[admin_pro.pk])
    content = verified_admin_client.get(url).content.decode()
    # The Jobirl token is a credential — never exposed.
    assert 'name="jobirl_user_token"' not in content
    assert "jobirl-token-do-not-show" not in content
    # The Jobirl id is set by the API, not by hand — shown read-only (visible, not editable).
    assert 'name="jobirl_user_id"' not in content
    assert "8675309" in content


@pytest.mark.django_db
def test_changelist_date_filter_renders(verified_admin_client, pros):
    response = verified_admin_client.get(
        reverse(CHANGELIST), {"created_at__gte": "2000-01-01 00:00:00+00:00"}
    )
    assert response.status_code == 200
