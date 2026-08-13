import pytest
from django.urls import reverse

USER_CHANGELIST = "admin:techpourtoutes_user_changelist"


@pytest.mark.django_db
@pytest.mark.parametrize("model_name", ["user", "pro"])
def test_admin_never_exposes_credential_fields(verified_admin_client, admin_pro, model_name):
    admin_pro.issue_login_token()  # populates login_token_hash
    admin_pro.refresh_from_db()
    url = reverse(f"admin:techpourtoutes_{model_name}_change", args=[admin_pro.pk])
    content = verified_admin_client.get(url).content.decode()
    # Credentials must never appear in the admin — not editable, not even displayed: a
    # password set here would be stored unhashed
    assert 'name="password"' not in content
    assert 'name="login_token_hash"' not in content
    assert admin_pro.password not in content
    assert admin_pro.login_token_hash not in content


@pytest.mark.django_db
def test_user_changelist_lists_details_without_engagements(verified_admin_client, pros):
    content = verified_admin_client.get(reverse(USER_CHANGELIST)).content.decode()
    # Same columns as the Pro list (names + email), minus the Pro-only engagements column.
    assert "Emma" in content
    assert "Martin" in content
    assert "emma@example.com" in content
    assert "mentorer" not in content


@pytest.mark.django_db
def test_user_changelist_search_and_date_filter(verified_admin_client, pros):
    by_name = verified_admin_client.get(reverse(USER_CHANGELIST), {"q": "Martin"}).content.decode()
    assert "emma@example.com" in by_name
    assert "bob@example.com" not in by_name

    dated = verified_admin_client.get(
        reverse(USER_CHANGELIST), {"created_at__gte": "2000-01-01 00:00:00+00:00"}
    )
    assert dated.status_code == 200
