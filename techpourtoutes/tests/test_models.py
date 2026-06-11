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
    assert values == {
        "mentor",
        "internships",
        "work_ambassador",
        "training_ambassador",
        "sponsor",
        "workshops",
    }


@pytest.mark.django_db
def test_pro_engagements_defaults_to_empty_list(valid_pro_model_data):
    from techpourtoutes.models import Pro

    Pro(username="marie.dupont@example.com", **valid_pro_model_data).save()
    saved = Pro.objects.get(email="marie.dupont@example.com")
    assert saved.engagements == []


@pytest.mark.django_db
def test_pro_workshops_engagement_is_valid(valid_pro_model_data):
    from techpourtoutes.models import Pro

    pro = Pro(username="marie.dupont@example.com", **valid_pro_model_data)
    pro.engagements = ["workshops"]
    pro.save()
    assert Pro.objects.get(email="marie.dupont@example.com").engagements == ["workshops"]


@pytest.mark.django_db
def test_pro_rejects_invalid_postal_code(valid_pro_model_data):
    from techpourtoutes.models import Pro

    data = {**valid_pro_model_data, "email": "badcp@example.com", "postal_code": "123"}
    with pytest.raises(ValidationError):
        Pro(username="badcp@example.com", **data).save()


@pytest.mark.django_db
def test_add_engagement_appends_new_engagement(valid_pro_model_data):
    from techpourtoutes.models import Pro

    pro = Pro(username="marie.dupont@example.com", **valid_pro_model_data)
    pro.add_engagement(Pro.Engagement.MENTOR)
    assert pro.engagements == ["mentor"]


@pytest.mark.django_db
def test_add_engagement_is_idempotent(valid_pro_model_data):
    from techpourtoutes.models import Pro

    pro = Pro(username="marie.dupont@example.com", **valid_pro_model_data)
    pro.add_engagement(Pro.Engagement.MENTOR)
    pro.add_engagement(Pro.Engagement.MENTOR)
    assert pro.engagements == ["mentor"]


@pytest.mark.django_db
def test_add_engagement_does_not_save(valid_pro_model_data):
    from techpourtoutes.models import Pro

    pro = Pro(username="marie.dupont@example.com", **valid_pro_model_data)
    pro.save()
    pro.add_engagement(Pro.Engagement.SPONSOR)
    assert Pro.objects.get(pk=pro.pk).engagements == []


@pytest.mark.django_db
def test_pro_phone_is_optional(valid_pro_model_data):
    from techpourtoutes.models import Pro

    data = {**valid_pro_model_data, "email": "sansinfos@example.com", "phone": ""}
    Pro(username="sansinfos@example.com", **data).save()

    assert Pro.objects.get(email="sansinfos@example.com").phone == ""


@pytest.mark.django_db
def test_pro_stores_structure_id(valid_pro_model_data):
    from techpourtoutes.models import Pro

    Pro(
        username="marie.dupont@example.com", structure_id="0123456A", **valid_pro_model_data
    ).save()
    assert Pro.objects.get(email="marie.dupont@example.com").structure_id == "0123456A"


@pytest.mark.django_db
def test_school_str_shows_name_and_postal_code():
    from techpourtoutes.models import School

    school = School(identifier="0750001A", name="Lycée Voltaire", postal_code="75011")
    school.save()
    assert str(school) == "Lycée Voltaire (75011)"


@pytest.mark.django_db
def test_school_identifier_is_unique():
    from techpourtoutes.models import School

    School(identifier="0750001A", name="Lycée Voltaire", postal_code="75011").save()
    with pytest.raises(ValidationError):
        School(identifier="0750001A", name="Autre lycée", postal_code="75012").save()


@pytest.mark.django_db
def test_workshop_request_links_to_pro_and_stores_data(pro):
    from techpourtoutes.models import WorkshopRequest

    req = WorkshopRequest(pro=pro, type="future_of_tech", remark="Top")
    req.save()

    assert list(pro.workshop_requests.all()) == [req]
    assert req.type == "future_of_tech"
    assert req.remark == "Top"
    assert req.created_at is not None


@pytest.mark.django_db
def test_workshop_request_rejects_invalid_type(pro):
    from techpourtoutes.models import WorkshopRequest

    with pytest.raises(ValidationError):
        WorkshopRequest(pro=pro, type="not-a-real-atelier").save()


@pytest.mark.django_db
def test_workshop_request_query_pros_by_type(pro):
    from techpourtoutes.models import Pro, WorkshopRequest

    WorkshopRequest(pro=pro, type="future_of_tech").save()

    matching = Pro.objects.filter(workshop_requests__type="future_of_tech")
    assert pro in matching


def test_strip_accents():
    from techpourtoutes.text import strip_accents

    assert strip_accents("Lycée privée à Nîmes") == "Lycee privee a Nimes"


@pytest.mark.django_db
def test_school_save_populates_normalized_name():
    from techpourtoutes.models import School

    school = School(identifier="0750001A", name="Lycée Privée", postal_code="75001")
    school.save()
    assert school.name_normalized == "Lycee Privee"


@pytest.mark.django_db
def test_training_experience_links_pro_and_higher_ed_school(pro, higher_ed_school):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(
        pro=pro, higher_ed_school=higher_ed_school, course="Master Informatique"
    )
    experience.save()

    assert experience in pro.training_experiences.all()
    assert experience in higher_ed_school.training_experiences.all()
