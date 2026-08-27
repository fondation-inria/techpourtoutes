import pytest
from django.core.exceptions import ValidationError


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
def test_soft_delete_anonymizes_expected_fields(pro):
    original_pk = pro.pk
    pro.faveod_id = 4242
    pro.save()
    original_professional_situation = pro.professional_situation
    original_engagements = pro.engagements
    original_postal_code = pro.postal_code
    original_structure_name = pro.structure_name
    original_civility = pro.civility
    original_job_title = pro.job_title

    pro.soft_delete()
    pro.refresh_from_db()

    assert not pro.is_active
    assert not pro.has_usable_password()
    assert pro.first_name == "Prénom"
    assert pro.last_name == "Nom"
    assert pro.username == f"deleted_{original_pk}"
    assert pro.email == f"deleted_{original_pk}@deleted.local"
    assert pro.login_token_hash == ""
    assert pro.login_token_expires_at is None
    assert not pro.brevo_sync_enabled

    assert pro.phone == ""
    assert pro.faveod_id is None
    assert pro.jobirl_user_id is None
    assert pro.jobirl_user_token == ""

    assert pro.professional_situation == original_professional_situation
    assert pro.engagements == original_engagements
    assert pro.postal_code == original_postal_code
    assert pro.structure_name == original_structure_name
    assert pro.civility == original_civility
    assert pro.job_title == original_job_title
