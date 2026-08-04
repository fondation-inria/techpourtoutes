import pytest

from techpourtoutes.models import Pro


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
