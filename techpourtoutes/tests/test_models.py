import hashlib
import uuid
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone


@pytest.mark.django_db
def test_user_has_uuid_pk():
    from techpourtoutes.models import User

    user = User.objects.create_user(username="test@example.com", email="test@example.com")
    assert isinstance(user.pk, uuid.UUID)


@pytest.mark.django_db
def test_mentor_inherits_user():
    from techpourtoutes.models import Mentor, User

    assert issubclass(Mentor, User)


@pytest.mark.django_db
def test_mentor_save_sets_unusable_password(valid_mentor_model_data):
    from techpourtoutes.models import Mentor

    mentor = Mentor(username="marie.dupont@example.com", **valid_mentor_model_data)
    mentor.save()
    assert not mentor.has_usable_password()


@pytest.mark.django_db
def test_mentor_creation_saves_all_fields(valid_mentor_model_data):
    from techpourtoutes.models import Mentor

    Mentor(username="marie.dupont@example.com", **valid_mentor_model_data).save()

    saved = Mentor.objects.get(email="marie.dupont@example.com")
    assert saved.civility == "Madame"
    assert saved.first_name == "Marie"
    assert saved.last_name == "Dupont"
    assert saved.email == "marie.dupont@example.com"
    assert saved.phone.national_number == 612345678
    assert saved.professional_situation == "working"
    assert saved.postal_code == "75011"
    assert saved.city == "Paris"
    assert saved.job_title == "Développeuse backend"
    assert saved.structure_name == "Grande entreprise"


@pytest.mark.django_db
def test_mentor_structure_name_optional(valid_mentor_model_data):
    from techpourtoutes.models import Mentor

    data = {**valid_mentor_model_data, "email": "autre@example.com", "structure_name": ""}
    Mentor(username="autre@example.com", **data).save()
    assert Mentor.objects.filter(email="autre@example.com").exists()


@pytest.mark.django_db
def test_mentor_save_raises_if_invalid(valid_mentor_model_data):
    from techpourtoutes.models import Mentor

    data = {**valid_mentor_model_data, "email": "not-an-email"}
    mentor = Mentor(username="bad@example.com", **data)
    with pytest.raises(ValidationError):
        mentor.save()


@pytest.mark.django_db
def test_issue_login_token_returns_plaintext_and_stores_hash(mentor):
    plaintext = mentor.issue_login_token()

    assert plaintext
    expected_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    mentor.refresh_from_db()
    assert mentor.login_token_hash == expected_hash
    assert mentor.login_token_hash != plaintext


@pytest.mark.django_db
def test_issue_login_token_sets_expiry_one_hour_ahead(mentor):
    before = timezone.now()
    mentor.issue_login_token()
    after = timezone.now()

    mentor.refresh_from_db()
    assert before + timedelta(hours=1) - timedelta(seconds=5) <= mentor.login_token_expires_at
    assert mentor.login_token_expires_at <= after + timedelta(hours=1) + timedelta(seconds=5)


@pytest.mark.django_db
def test_issue_login_token_twice_overwrites_previous(mentor):
    first = mentor.issue_login_token()
    second = mentor.issue_login_token()

    assert first != second
    mentor.refresh_from_db()
    assert mentor.login_token_hash == hashlib.sha256(second.encode()).hexdigest()


@pytest.mark.django_db
def test_consume_login_token_returns_user_and_clears_hash(mentor):
    from techpourtoutes.models import User

    plaintext = mentor.issue_login_token()

    consumed = User.consume_login_token(plaintext=plaintext)

    assert consumed is not None
    assert consumed.pk == mentor.pk
    mentor.refresh_from_db()
    assert mentor.login_token_hash == ""
    assert mentor.login_token_expires_at is None


@pytest.mark.django_db
def test_consume_login_token_returns_none_for_garbage():
    from techpourtoutes.models import User

    assert User.consume_login_token(plaintext="not-a-real-token") is None


@pytest.mark.django_db
def test_consume_login_token_returns_none_when_expired(mentor):
    from techpourtoutes.models import User

    plaintext = mentor.issue_login_token()
    mentor.login_token_expires_at = timezone.now() - timedelta(minutes=1)
    mentor.save()

    assert User.consume_login_token(plaintext=plaintext) is None


@pytest.mark.django_db
def test_consume_login_token_returns_none_on_second_use(mentor):
    from techpourtoutes.models import User

    plaintext = mentor.issue_login_token()
    assert User.consume_login_token(plaintext=plaintext) is not None
    assert User.consume_login_token(plaintext=plaintext) is None
