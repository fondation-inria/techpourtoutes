import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from techpourtoutes.models import Beneficiary, Pro, TrainingExperience


@pytest.mark.django_db
def test_seed_refuses_when_disabled():
    with override_settings(SEED_ENABLED=False):
        with pytest.raises(CommandError):
            call_command("seed")


@pytest.mark.django_db
def test_seed_creates_admin_pro_with_configured_credentials():
    with override_settings(
        SEED_ENABLED=True,
        SEED_ADMIN_EMAIL="reviewer@example.com",
        SEED_ADMIN_PASSWORD="s3cret-review-pass",
    ):
        call_command("seed")

    pro = Pro.objects.get(email="reviewer@example.com")
    assert pro.check_password("s3cret-review-pass")


@pytest.mark.django_db
def test_seed_is_idempotent():
    with override_settings(SEED_ENABLED=True):
        call_command("seed")
        call_command("seed")

    assert Pro.objects.filter(email="admin@techpourtoutes.io").count() == 1


@pytest.mark.django_db
def test_seed_creates_beneficiary_with_configured_credentials():
    with override_settings(
        SEED_ENABLED=True,
        SEED_BENEFICIARY_EMAIL="reviewer-beneficiary@example.com",
        SEED_BENEFICIARY_PASSWORD="s3cret-review-pass",
    ):
        call_command("seed")

    beneficiary = Beneficiary.objects.get(email="reviewer-beneficiary@example.com")
    assert beneficiary.check_password("s3cret-review-pass")
    assert TrainingExperience.objects.filter(user=beneficiary).exists()


@pytest.mark.django_db
def test_seed_beneficiary_is_idempotent():
    with override_settings(SEED_ENABLED=True):
        call_command("seed")
        call_command("seed")

    assert Beneficiary.objects.filter(email="beneficiary@techpourtoutes.io").count() == 1
    assert (
        TrainingExperience.objects.filter(user__email="beneficiary@techpourtoutes.io").count() == 1
    )
