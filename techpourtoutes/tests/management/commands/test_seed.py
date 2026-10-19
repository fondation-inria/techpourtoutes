import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from techpourtoutes.models import Beneficiary, Event, Pro, TrainingExperience
from techpourtoutes.utils.dates import compute_age


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
def test_seed_creates_an_adult_student_a_minor_pupil_and_an_admin_pro_per_team_email():
    with override_settings(
        SEED_ENABLED=True,
        SEED_ADMIN_PASSWORD="s3cret-review-pass",
        SEED_TEAM_EMAILS=["abc@example.com", "def@example.com"],
    ):
        call_command("seed")

    for name in ("abc", "def"):
        student = Beneficiary.objects.get(email=f"{name}+etudiante@example.com")
        assert compute_age(student.birth_date) >= 18
        assert student.training_experiences.get().formation.higher_ed

        pupil = Beneficiary.objects.get(email=f"{name}+lyceenne@example.com")
        assert compute_age(pupil.birth_date) < 18
        assert pupil.training_experiences.get().formation.secondary

        pro = Pro.objects.get(email=f"{name}+pro@example.com")
        assert pro.is_superuser
        assert pro.check_password("s3cret-review-pass")


@pytest.mark.django_db
def test_seed_team_accounts_are_idempotent():
    with override_settings(SEED_ENABLED=True, SEED_TEAM_EMAILS=["abc@example.com"]):
        call_command("seed")
        call_command("seed")

    assert Beneficiary.objects.filter(email__startswith="abc+").count() == 2
    assert Pro.objects.filter(email__startswith="abc+").count() == 1


@pytest.mark.django_db
def test_seed_team_accounts_replace_the_default_ones():
    from techpourtoutes.models import Event

    with override_settings(SEED_ENABLED=True, SEED_TEAM_EMAILS=["abc@example.com"]):
        call_command("seed")

    assert not Pro.objects.filter(email="admin@techpourtoutes.io").exists()
    assert not Beneficiary.objects.filter(email="beneficiary@techpourtoutes.io").exists()
    assert Event.objects.filter(created_by__email="abc+pro@example.com").exists()


@pytest.mark.django_db
def test_seed_creates_one_approved_upcoming_event_per_category():
    with override_settings(SEED_ENABLED=True):
        call_command("seed")

    events = Event.objects.approved().upcoming()
    assert {event.category for event in events} == set(Event.Category)


@pytest.mark.django_db
def test_seed_events_have_multiline_descriptions():
    with override_settings(SEED_ENABLED=True):
        call_command("seed")

    events = Event.objects.all()
    assert events.exists()
    for event in events:
        assert "\n\n" in event.description


@pytest.mark.django_db
def test_seed_includes_events_that_require_registration_or_candidacy():
    """A few seeded events carry a real registration link, so the participation CTA is testable."""

    with override_settings(SEED_ENABLED=True):
        call_command("seed")

    non_open = Event.objects.exclude(access_type=Event.AccessType.OPEN)
    assert non_open.exists()
    assert all(event.registration_url for event in non_open)
