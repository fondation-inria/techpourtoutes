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
    ):
        call_command("seed")

    beneficiary = Beneficiary.objects.get(email="reviewer-beneficiary@example.com")
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


@pytest.mark.django_db
def test_seed_creates_one_approved_upcoming_event_per_category():
    from techpourtoutes.models import Event

    with override_settings(SEED_ENABLED=True):
        call_command("seed")

    events = Event.objects.approved().upcoming()
    assert {event.category for event in events} == set(Event.Category)


@pytest.mark.django_db
def test_seed_events_have_multiline_descriptions():
    from techpourtoutes.models import Event

    with override_settings(SEED_ENABLED=True):
        call_command("seed")

    events = Event.objects.all()
    assert events.exists()
    for event in events:
        assert "\n\n" in event.description


@pytest.mark.django_db
def test_seed_includes_events_that_require_registration_or_candidacy():
    """A few seeded events carry a real registration link, so the participation CTA is testable."""
    from techpourtoutes.models import Event

    with override_settings(SEED_ENABLED=True):
        call_command("seed")

    non_open = Event.objects.exclude(access_type=Event.AccessType.OPEN)
    assert non_open.exists()
    assert all(event.registration_url for event in non_open)
