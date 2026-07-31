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
    assert saved.phone.national_number == 612345678
    assert saved.professional_situation == "working"


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


@pytest.mark.django_db
def test_issue_login_code_stores_hash_and_resets_attempts(pro):
    pro.login_code_attempts = 3
    pro.save()

    code = pro.issue_login_code()

    assert len(code) == 6 and code.isdigit()
    pro.refresh_from_db()
    assert pro.login_code_hash == hashlib.sha256(code.encode()).hexdigest()
    assert pro.login_code_hash != code
    assert pro.login_code_attempts == 0
    assert pro.login_code_expires_at > timezone.now()


@pytest.mark.django_db
def test_consume_login_code_returns_true_on_match(pro):
    code = pro.issue_login_code()

    assert pro.consume_login_code(code) is True


@pytest.mark.django_db
def test_consume_login_code_consumes_code_on_success(pro):
    from techpourtoutes.models import User

    code = pro.issue_login_code()

    assert pro.consume_login_code(code) is True

    fresh = User.objects.get(pk=pro.pk)
    assert fresh.login_code_hash == ""
    assert fresh.consume_login_code(code) is False


@pytest.mark.django_db
def test_consume_login_code_is_single_use_under_concurrent_verify(pro):
    from techpourtoutes.models import User

    code = pro.issue_login_code()
    first = User.objects.get(pk=pro.pk)
    second = User.objects.get(pk=pro.pk)

    results = [first.consume_login_code(code), second.consume_login_code(code)]

    assert results.count(True) == 1


@pytest.mark.django_db
def test_consume_login_code_wrong_increments_attempts(pro):
    pro.issue_login_code()

    assert pro.consume_login_code("000000") is False
    pro.refresh_from_db()
    assert pro.login_code_attempts == 1


@pytest.mark.django_db
def test_consume_login_code_false_when_no_code(pro):
    assert pro.consume_login_code("123456") is False


@pytest.mark.django_db
def test_consume_login_code_false_when_expired(pro):
    code = pro.issue_login_code()
    pro.login_code_expires_at = timezone.now() - timedelta(minutes=1)
    pro.save()

    assert pro.consume_login_code(code) is False


@pytest.mark.django_db
def test_consume_login_code_false_when_locked(pro):
    from techpourtoutes.models.user import VERIFICATION_CODE_MAX_ATTEMPTS

    code = pro.issue_login_code()
    pro.login_code_attempts = VERIFICATION_CODE_MAX_ATTEMPTS
    pro.save()

    assert pro.consume_login_code(code) is False


@pytest.mark.django_db
def test_consume_login_code_clears_code_on_final_wrong_attempt(pro):
    from techpourtoutes.models.user import VERIFICATION_CODE_MAX_ATTEMPTS

    pro.issue_login_code()
    pro.login_code_attempts = VERIFICATION_CODE_MAX_ATTEMPTS - 1
    pro.save()

    assert pro.consume_login_code("000000") is False
    pro.refresh_from_db()
    assert pro.login_code_hash == ""


@pytest.mark.django_db
def test_set_email_change_code_stores_hash_and_resets_attempts(pro):
    pro.email_change_attempts = 3
    pro.save()

    code = pro.set_email_change_code()

    assert code
    assert len(code) == 6 and code.isdigit()
    pro.refresh_from_db()
    assert pro.email_change_code_hash == hashlib.sha256(code.encode()).hexdigest()
    assert pro.email_change_code_hash != code
    assert pro.email_change_attempts == 0


@pytest.mark.django_db
def test_consume_email_change_code_returns_true_on_match(pro):
    code = pro.set_email_change_code()

    assert pro.consume_email_change_code(code) is True


@pytest.mark.django_db
def test_consume_email_change_code_consumes_code_on_success(pro):
    from techpourtoutes.models import User

    code = pro.set_email_change_code()

    assert pro.consume_email_change_code(code) is True

    fresh = User.objects.get(pk=pro.pk)
    assert fresh.email_change_code_hash == ""
    assert fresh.consume_email_change_code(code) is False


@pytest.mark.django_db
def test_consume_email_change_code_is_single_use_under_concurrent_verify(pro):
    from techpourtoutes.models import User

    code = pro.set_email_change_code()
    first = User.objects.get(pk=pro.pk)
    second = User.objects.get(pk=pro.pk)

    results = [first.consume_email_change_code(code), second.consume_email_change_code(code)]

    assert results.count(True) == 1


@pytest.mark.django_db
def test_consume_email_change_code_wrong_increments_attempts(pro):
    pro.set_email_change_code()

    assert pro.consume_email_change_code("000000") is False
    pro.refresh_from_db()
    assert pro.email_change_attempts == 1


@pytest.mark.django_db
def test_consume_email_change_code_false_when_no_code(pro):
    assert pro.consume_email_change_code("123456") is False


@pytest.mark.django_db
def test_consume_email_change_code_false_when_locked(pro):
    from techpourtoutes.models.user import VERIFICATION_CODE_MAX_ATTEMPTS

    code = pro.set_email_change_code()
    pro.email_change_attempts = VERIFICATION_CODE_MAX_ATTEMPTS
    pro.save()

    assert pro.consume_email_change_code(code) is False


@pytest.mark.django_db
def test_apply_email_change_updates_email_and_username_and_clears(pro):
    pro.set_email_change_code()

    pro.apply_email_change("nouvelle@example.com")

    pro.refresh_from_db()
    assert pro.email == "nouvelle@example.com"
    assert pro.username == "nouvelle@example.com"
    assert pro.email_change_code_hash == ""
    assert pro.email_change_attempts == 0


@pytest.mark.django_db
def test_email_change_token_round_trip(pro):
    token = pro.issue_email_change_token("nouvelle@example.com", "current")

    assert pro.read_email_change_token(token) == {
        "user_pk": str(pro.pk),
        "new_email": "nouvelle@example.com",
        "stage": "current",
    }


@pytest.mark.django_db
def test_read_email_change_token_rejects_tampered_token(pro):
    token = pro.issue_email_change_token("nouvelle@example.com", "current")

    assert pro.read_email_change_token(token + "x") is None


@pytest.mark.django_db
def test_consume_email_change_code_false_when_expired(pro):
    code = pro.set_email_change_code()
    pro.email_change_code_expires_at = timezone.now() - timedelta(minutes=1)
    pro.save()

    assert pro.consume_email_change_code(code) is False


@pytest.mark.django_db
def test_read_email_change_token_rejects_other_user(pro, inactive_user):
    token = pro.issue_email_change_token("nouvelle@example.com", "current")

    assert inactive_user.read_email_change_token(token) is None


@pytest.mark.django_db
def test_email_change_verify_url_carries_token(pro):
    from urllib.parse import urlencode

    from django.urls import reverse

    token = pro.issue_email_change_token("nouvelle@example.com", "current")
    url = pro.email_change_verify_url(token)

    assert url.startswith(reverse("email_change_verify"))
    assert urlencode({"token": token}) in url


@pytest.mark.django_db
def test_pro_engagements_defaults_to_empty_list(valid_pro_model_data):
    from techpourtoutes.models import Pro

    Pro(username="marie.dupont@example.com", **valid_pro_model_data).save()
    saved = Pro.objects.get(email="marie.dupont@example.com")
    assert saved.engagements == []


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
        user=pro, higher_ed_school=higher_ed_school, course="Master Informatique"
    )
    experience.save()

    assert experience in pro.training_experiences.all()
    assert experience in higher_ed_school.training_experiences.all()


@pytest.mark.django_db
def test_beneficiary_creation_saves_all_fields():
    from datetime import date

    from techpourtoutes.models import Beneficiary

    beneficiary = Beneficiary(
        username="jade@example.com",
        first_name="Jade",
        last_name="Petit",
        email="jade@example.com",
        birth_date=date(2008, 3, 15),
        postal_code="75011",
    )
    beneficiary.save()

    saved = Beneficiary.objects.get(email="jade@example.com")
    assert saved.first_name == "Jade"
    assert saved.birth_date == date(2008, 3, 15)
    assert saved.postal_code == "75011"


@pytest.mark.django_db
def test_beneficiary_rejects_invalid_postal_code():
    from datetime import date

    from techpourtoutes.models import Beneficiary

    beneficiary = Beneficiary(
        username="jade@example.com",
        first_name="Jade",
        last_name="Petit",
        email="jade@example.com",
        birth_date=date(2008, 3, 15),
        postal_code="123",
    )
    with pytest.raises(ValidationError):
        beneficiary.save()


@pytest.mark.django_db
def test_training_experience_links_beneficiary_and_school(beneficiary, school):
    from datetime import date

    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.TERMINALE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        course="Spécialité mathématiques",
    )
    experience.save()

    assert experience in beneficiary.training_experiences.all()
    assert experience in school.training_experiences.all()


@pytest.mark.django_db
def test_training_experience_links_beneficiary_and_higher_ed_school(beneficiary, higher_ed_school):
    from datetime import date

    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(
        user=beneficiary,
        higher_ed_school=higher_ed_school,
        level=TrainingExperience.Level.BAC_1,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        course="Licence informatique",
    )
    experience.save()

    assert experience in beneficiary.training_experiences.all()
    assert experience in higher_ed_school.training_experiences.all()


@pytest.mark.django_db
def test_training_experiences_are_ordered_reverse_chronologically(beneficiary, school):
    from datetime import date

    from techpourtoutes.models import TrainingExperience

    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.TERMINALE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        course="Terminale",
    )
    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.SECONDE,
        start_date=date(2022, 9, 1),
        end_date=date(2023, 8, 31),
        course="Seconde",
    )
    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.PREMIERE,
        start_date=date(2023, 9, 1),
        end_date=date(2024, 8, 31),
        course="Première",
    )

    labels = [experience.period_label for experience in beneficiary.training_experiences.all()]
    assert labels == ["2024-2025", "2023-2024", "2022-2023"]


@pytest.mark.django_db
def test_training_experience_rejects_duplicate_period_label_for_same_beneficiary(
    beneficiary, school
):
    from datetime import date

    from techpourtoutes.models import TrainingExperience

    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.TERMINALE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        course="Terminale",
    )
    duplicate = TrainingExperience(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.PREMIERE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        course="Première",
    )

    with pytest.raises(ValidationError):
        duplicate.save()


def test_current_school_year_start_date_before_rollover_month(monkeypatch):
    from datetime import date

    from techpourtoutes.models.training_experience import current_school_year_start_date

    monkeypatch.setattr(
        "techpourtoutes.models.training_experience.timezone.localdate",
        lambda: date(2026, 3, 15),
    )

    assert current_school_year_start_date() == date(2025, 9, 1)


def test_current_school_year_start_date_after_rollover_month(monkeypatch):
    from datetime import date

    from techpourtoutes.models.training_experience import current_school_year_start_date

    monkeypatch.setattr(
        "techpourtoutes.models.training_experience.timezone.localdate",
        lambda: date(2026, 9, 1),
    )

    assert current_school_year_start_date() == date(2026, 9, 1)


def test_school_year_choices_ranges_from_ten_years_back_to_next_year(monkeypatch):
    from datetime import date

    from techpourtoutes.models.training_experience import school_year_choices

    monkeypatch.setattr(
        "techpourtoutes.models.training_experience.timezone.localdate",
        lambda: date(2026, 3, 15),
    )

    choices = school_year_choices()

    assert choices[0] == ("2026-2027", "2026-2027")
    assert choices[-1] == ("2015-2016", "2015-2016")
    assert len(choices) == 12


def test_training_experience_is_current_school_year():
    from datetime import date

    from techpourtoutes.models import TrainingExperience
    from techpourtoutes.models.training_experience import current_school_year_start_date

    current = TrainingExperience(start_date=current_school_year_start_date())
    past = TrainingExperience(start_date=date(2000, 9, 1))

    assert current.is_current_school_year
    assert not past.is_current_school_year


@pytest.mark.django_db
def test_soft_delete_anonymizes_expected_fields(pro):
    original_pk = pro.pk
    original_professional_situation = pro.professional_situation
    original_engagements = pro.engagements
    original_structure_name = pro.structure_name
    original_structure_id = pro.structure_id
    original_civility = pro.civility
    original_job_title = pro.job_title

    pro.soft_delete()
    pro.save()
    pro.refresh_from_db()

    assert not pro.is_active
    assert not pro.has_usable_password()
    assert pro.first_name == ""
    assert pro.last_name == ""
    assert pro.username == f"deleted_{original_pk}"
    assert pro.email == f"deleted_{original_pk}@deleted.local"
    assert pro.login_token_hash == ""
    assert pro.login_token_expires_at is None
    assert not pro.brevo_sync_enabled

    assert pro.phone == ""
    assert pro.postal_code == ""
    assert pro.faveod_id is None
    assert pro.jobirl_user_id is None
    assert pro.jobirl_user_token == ""

    assert pro.professional_situation == original_professional_situation
    assert pro.engagements == original_engagements
    assert pro.structure_name == original_structure_name
    assert pro.structure_id == original_structure_id
    assert pro.civility == original_civility
    assert pro.job_title == original_job_title


@pytest.mark.django_db
def test_soft_delete_anonymizes_expected_fields_for_beneficiary(beneficiary):
    from techpourtoutes.models import Beneficiary

    original_pk = beneficiary.pk

    beneficiary.soft_delete()
    beneficiary.save()
    beneficiary.refresh_from_db()

    assert not beneficiary.is_active
    assert not beneficiary.has_usable_password()
    assert beneficiary.first_name == ""
    assert beneficiary.last_name == ""
    assert beneficiary.username == f"deleted_{original_pk}"
    assert beneficiary.email == f"deleted_{original_pk}@deleted.local"
    assert beneficiary.login_token_hash == ""
    assert beneficiary.login_token_expires_at is None
    assert not beneficiary.brevo_sync_enabled

    assert beneficiary.phone == ""
    assert beneficiary.postal_code == ""
    assert beneficiary.jobirl_user_id is None
    assert beneficiary.jobirl_user_token == ""

    assert isinstance(beneficiary, Beneficiary)
    assert beneficiary.birth_date is None
