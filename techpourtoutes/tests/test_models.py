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
def test_pro_inherits_user():
    from techpourtoutes.models import Pro, User

    assert issubclass(Pro, User)


@pytest.mark.django_db
def test_pro_save_sets_unusable_password(valid_pro_model_data):
    from techpourtoutes.models import Pro

    pro = Pro(username="marie.dupont@example.com", **valid_pro_model_data)
    pro.save()
    assert not pro.has_usable_password()


@pytest.mark.django_db
def test_pro_creation_saves_all_fields(valid_pro_model_data):
    from techpourtoutes.models import Pro

    Pro(username="marie.dupont@example.com", **valid_pro_model_data).save()

    saved = Pro.objects.get(email="marie.dupont@example.com")
    assert saved.civility == "Madame"
    assert saved.first_name == "Marie"
    assert saved.last_name == "Dupont"
    assert saved.email == "marie.dupont@example.com"
    assert saved.phone.national_number == 612345678
    assert saved.professional_situation == "working"
    assert saved.postal_code == "75011"
    assert saved.job_title == "Développeuse backend"
    assert saved.structure_name == "Grande entreprise"


@pytest.mark.django_db
def test_pro_structure_name_optional(valid_pro_model_data):
    from techpourtoutes.models import Pro

    data = {**valid_pro_model_data, "email": "autre@example.com", "structure_name": ""}
    Pro(username="autre@example.com", **data).save()
    assert Pro.objects.filter(email="autre@example.com").exists()


@pytest.mark.django_db
def test_pro_save_raises_if_invalid(valid_pro_model_data):
    from techpourtoutes.models import Pro

    data = {**valid_pro_model_data, "email": "not-an-email"}
    pro = Pro(username="bad@example.com", **data)
    with pytest.raises(ValidationError):
        pro.save()


@pytest.mark.django_db
def test_issue_login_token_returns_plaintext_and_stores_hash(pro):
    plaintext = pro.issue_login_token()

    assert plaintext
    expected_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    pro.refresh_from_db()
    assert pro.login_token_hash == expected_hash
    assert pro.login_token_hash != plaintext


@pytest.mark.django_db
def test_issue_login_token_sets_expiry_one_hour_ahead(pro):
    before = timezone.now()
    pro.issue_login_token()
    after = timezone.now()

    pro.refresh_from_db()
    assert before + timedelta(hours=1) - timedelta(seconds=5) <= pro.login_token_expires_at
    assert pro.login_token_expires_at <= after + timedelta(hours=1) + timedelta(seconds=5)


@pytest.mark.django_db
def test_issue_login_token_twice_overwrites_previous(pro):
    first = pro.issue_login_token()
    second = pro.issue_login_token()

    assert first != second
    pro.refresh_from_db()
    assert pro.login_token_hash == hashlib.sha256(second.encode()).hexdigest()


@pytest.mark.django_db
def test_consume_login_token_returns_user_and_clears_hash(pro):
    from techpourtoutes.models import User

    plaintext = pro.issue_login_token()

    consumed = User.consume_login_token(plaintext=plaintext)

    assert consumed is not None
    assert consumed.pk == pro.pk
    pro.refresh_from_db()
    assert pro.login_token_hash == ""
    assert pro.login_token_expires_at is None


@pytest.mark.django_db
def test_consume_login_token_returns_none_for_garbage():
    from techpourtoutes.models import User

    assert User.consume_login_token(plaintext="not-a-real-token") is None


@pytest.mark.django_db
def test_consume_login_token_returns_none_when_expired(pro):
    from techpourtoutes.models import User

    plaintext = pro.issue_login_token()
    pro.login_token_expires_at = timezone.now() - timedelta(minutes=1)
    pro.save()

    assert User.consume_login_token(plaintext=plaintext) is None


@pytest.mark.django_db
def test_consume_login_token_returns_none_on_second_use(pro):
    from techpourtoutes.models import User

    plaintext = pro.issue_login_token()
    assert User.consume_login_token(plaintext=plaintext) is not None
    assert User.consume_login_token(plaintext=plaintext) is None


def test_pro_engagement_choices():
    from techpourtoutes.models import Pro

    values = {e.value for e in Pro.Engagement}
    assert values == {"mentor", "internships", "work_ambassador", "training_ambassador", "sponsor"}


@pytest.mark.django_db
def test_pro_engagements_defaults_to_empty_list(valid_pro_model_data):
    from techpourtoutes.models import Pro

    Pro(username="marie.dupont@example.com", **valid_pro_model_data).save()
    saved = Pro.objects.get(email="marie.dupont@example.com")
    assert saved.engagements == []
