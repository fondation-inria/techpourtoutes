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
def admin_pro(db):
    pro = Pro(
        username="admin@example.com",
        civility=Pro.Civility.MADAME,
        first_name="Admin",
        last_name="Martin",
        email="admin@example.com",
        phone="+33612345678",
        postal_code="75001",
        professional_situation=Pro.ProfessionalSituation.WORKING,
        job_title="Admin",
        structure_name="Inria",
        is_staff=True,
        is_superuser=True,
    )
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


@pytest.mark.django_db
def test_admin_requires_verified_otp_device(client, admin_pro):
    client.force_login(admin_pro)  # authenticated, but no verified second factor
    assert client.get(reverse("admin:index")).status_code == 302


@pytest.mark.django_db
def test_admin_accessible_with_verified_otp_device(verified_admin_client):
    assert verified_admin_client.get(reverse("admin:index")).status_code == 200


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
