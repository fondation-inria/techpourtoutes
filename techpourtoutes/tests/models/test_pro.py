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
def test_pro_stores_structure_id(valid_pro_model_data):
    from techpourtoutes.models import Pro

    Pro(
        username="marie.dupont@example.com", structure_id="0123456A", **valid_pro_model_data
    ).save()
    assert Pro.objects.get(email="marie.dupont@example.com").structure_id == "0123456A"
