import importlib

import pytest
from django.test import override_settings
from django.urls import clear_url_caches, reverse

from techpourtoutes.models import Pro


@pytest.mark.django_db
def test_admin_mounts_at_configured_url(client):
    import conf.urls

    try:
        with override_settings(ADMIN_URL="secret-mgmt"):
            importlib.reload(conf.urls)
            clear_url_caches()
            # The configured path resolves (redirects to login); the default does not exist.
            assert client.get("/secret-mgmt/").status_code != 404
            assert client.get("/admin/").status_code == 404
    finally:
        importlib.reload(conf.urls)
        clear_url_caches()


@pytest.fixture
def admin_pro(pro):
    pro.is_staff = True
    pro.is_superuser = True
    pro.save()
    pro.set_password("initial-pass")
    pro.save(update_fields=["password"])
    return pro


@pytest.fixture
def verified_admin_client(client, admin_pro):
    from django_otp import DEVICE_ID_SESSION_KEY
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.create(user=admin_pro, name="default", confirmed=True)
    client.force_login(admin_pro)
    session = client.session
    session[DEVICE_ID_SESSION_KEY] = device.persistent_id
    session.save()
    return client


CHANGELIST = "admin:techpourtoutes_pro_changelist"


def _make_pro_with_engagements(email, first_name, last_name, engagements):
    pro = Pro(
        username=email,
        civility=Pro.Civility.MADAME,
        first_name=first_name,
        last_name=last_name,
        email=email,
        professional_situation=Pro.ProfessionalSituation.WORKING,
        engagements=engagements,
    )
    pro.save()
    return pro


@pytest.fixture
def pros(db):
    return {
        "mentor": _make_pro_with_engagements(
            "emma@example.com", "Emma", "Martin", [Pro.Engagement.MENTOR]
        ),
        "sponsor": _make_pro_with_engagements(
            "bob@example.com", "Bob", "Lefevre", [Pro.Engagement.SPONSOR]
        ),
        "ambassador": _make_pro_with_engagements(
            "carol@example.com", "Carol", "Moreau", [Pro.Engagement.WORK_AMBASSADOR]
        ),
    }


@pytest.mark.django_db
def test_admin_requires_verified_otp_device(client, admin_pro):
    client.force_login(admin_pro)  # authenticated, but no verified second factor
    assert client.get(reverse("admin:index")).status_code == 302


@pytest.mark.django_db
def test_admin_accessible_with_verified_otp_device(verified_admin_client):
    assert verified_admin_client.get(reverse("admin:index")).status_code == 200


@pytest.mark.django_db
def test_admin_2fa_can_be_disabled_outside_debug(client, admin_pro):
    client.force_login(admin_pro)  # authenticated, no verified second factor
    with override_settings(DISABLE_ADMIN_2FA=True):
        assert client.get(reverse("admin:index")).status_code == 200


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
def test_changelist_date_filter_renders(verified_admin_client, pros):
    response = verified_admin_client.get(
        reverse(CHANGELIST), {"created_at__gte": "2000-01-01 00:00:00+00:00"}
    )
    assert response.status_code == 200


USER_CHANGELIST = "admin:techpourtoutes_user_changelist"


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
