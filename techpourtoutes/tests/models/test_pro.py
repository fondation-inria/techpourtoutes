import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError

from techpourtoutes.models import Pro


@pytest.mark.django_db
def test_pro_save_sets_unusable_password(valid_pro_model_data):
    pro = Pro(username="marie.dupont@example.com", **valid_pro_model_data)
    pro.save()
    assert not pro.has_usable_password()


@pytest.mark.django_db
def test_pro_creation_saves_all_fields(valid_pro_model_data):
    Pro(username="marie.dupont@example.com", **valid_pro_model_data).save()

    saved = Pro.objects.get(email="marie.dupont@example.com")
    assert saved.phone.national_number == 612345678
    assert saved.structure_type == "company"


@pytest.mark.django_db
def test_pro_structure_name_optional(valid_pro_model_data):
    data = {**valid_pro_model_data, "email": "autre@example.com", "structure_name": ""}
    Pro(username="autre@example.com", **data).save()
    assert Pro.objects.filter(email="autre@example.com").exists()


@pytest.mark.django_db
def test_pro_save_raises_if_invalid(valid_pro_model_data):
    data = {**valid_pro_model_data, "email": "not-an-email"}
    pro = Pro(username="bad@example.com", **data)
    with pytest.raises(ValidationError):
        pro.save()


@pytest.mark.django_db
def test_pro_engagements_defaults_to_empty_list(valid_pro_model_data):
    Pro(username="marie.dupont@example.com", **valid_pro_model_data).save()
    saved = Pro.objects.get(email="marie.dupont@example.com")
    assert saved.engagements == []


@pytest.mark.django_db
def test_pro_rejects_invalid_postal_code(valid_pro_model_data):
    data = {**valid_pro_model_data, "email": "badcp@example.com", "postal_code": "123"}
    with pytest.raises(ValidationError):
        Pro(username="badcp@example.com", **data).save()


@pytest.mark.django_db
def test_add_engagement_appends_new_engagement(valid_pro_model_data):
    pro = Pro(username="marie.dupont@example.com", **valid_pro_model_data)
    pro.add_engagement(Pro.Engagement.MENTOR)
    assert pro.engagements == ["mentor"]


@pytest.mark.django_db
def test_add_engagement_is_idempotent(valid_pro_model_data):
    pro = Pro(username="marie.dupont@example.com", **valid_pro_model_data)
    pro.add_engagement(Pro.Engagement.MENTOR)
    pro.add_engagement(Pro.Engagement.MENTOR)
    assert pro.engagements == ["mentor"]


@pytest.mark.django_db
def test_add_engagement_does_not_save(valid_pro_model_data):
    pro = Pro(username="marie.dupont@example.com", **valid_pro_model_data)
    pro.save()
    pro.add_engagement(Pro.Engagement.SPONSOR)
    assert Pro.objects.get(pk=pro.pk).engagements == []


@pytest.mark.django_db
def test_pro_phone_is_optional(valid_pro_model_data):
    data = {**valid_pro_model_data, "email": "sansinfos@example.com", "phone": ""}
    Pro(username="sansinfos@example.com", **data).save()

    assert Pro.objects.get(email="sansinfos@example.com").phone == ""


@pytest.mark.django_db
def test_event_moderators_returns_whoever_may_moderate_events(
    pro, valid_pro_model_data, event_moderator_group
):
    """Held through a group, as the Chargée de mission holds it, or granted to one account."""

    grouped = Pro(
        username="chargee@example.com", **{**valid_pro_model_data, "email": "chargee@example.com"}
    )
    grouped.save()
    grouped.groups.add(event_moderator_group)
    granted = Pro(
        username="ponctuelle@example.com",
        **{**valid_pro_model_data, "email": "ponctuelle@example.com"},
    )
    granted.save()
    granted.user_permissions.add(
        Permission.objects.get(codename="change_event", content_type__app_label="techpourtoutes")
    )

    assert set(Pro.event_moderators()) == {grouped, granted}
    assert pro not in Pro.event_moderators()


@pytest.mark.django_db
def test_soft_delete_anonymizes_expected_fields(pro):
    original_pk = pro.pk
    pro.faveod_id = 4242
    pro.save()
    original_structure_type = pro.structure_type
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

    assert pro.structure_type == original_structure_type
    assert pro.engagements == original_engagements
    assert pro.postal_code == original_postal_code
    assert pro.structure_name == original_structure_name
    assert pro.civility == original_civility
    assert pro.job_title == original_job_title


@pytest.mark.django_db
def test_pro_saves_a_structure_type(pro):
    pro.structure_type = Pro.StructureType.ASSOCIATION
    pro.save()
    assert Pro.objects.get(pk=pro.pk).structure_type == "association"


@pytest.mark.django_db
def test_pro_may_mobilize_her_structure(pro):
    pro.add_engagement(Pro.Engagement.MOBILIZE_STRUCTURE)
    pro.save()
    assert Pro.objects.get(pk=pro.pk).engagements == ["mobilize_structure"]


@pytest.mark.parametrize(
    "engagements, expected",
    [
        ([], True),
        ([Pro.Engagement.TRAINING_AMBASSADOR], True),
        ([Pro.Engagement.MENTOR], False),
        ([Pro.Engagement.TRAINING_AMBASSADOR, Pro.Engagement.WORKSHOPS], False),
    ],
)
def test_may_be_training_ambassador_unless_another_engagement_was_taken(engagements, expected):
    assert Pro(engagements=engagements).may_be_training_ambassador is expected
