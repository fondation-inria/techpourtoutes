import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from techpourtoutes.models import Beneficiary, User
from techpourtoutes.services.brevo_api.mappings import brevo_attributes_for, brevo_list_id_for


@pytest.mark.django_db
def test_beneficiary_creation_is_passwordless_and_madame():
    beneficiary = Beneficiary(
        username="lea@example.com",
        email="lea@example.com",
        first_name="Léa",
        last_name="Petit",
    )
    beneficiary.save()

    assert not beneficiary.has_usable_password()
    assert beneficiary.civility == User.Civility.MADAME


@pytest.mark.django_db
def test_personal_fields_live_on_user():
    beneficiary = Beneficiary(
        username="lea@example.com",
        email="lea@example.com",
        first_name="Léa",
        last_name="Petit",
    )
    beneficiary.save()

    user = User.objects.get(pk=beneficiary.pk)
    assert user.civility == User.Civility.MADAME
    assert hasattr(user, "phone")
    assert hasattr(user, "postal_code")


@override_settings(BREVO_BENEFICIARY_LIST_ID=99, BREVO_PRO_LIST_ID=1)
@pytest.mark.django_db
def test_beneficiary_syncs_to_its_own_brevo_list():
    beneficiary = Beneficiary(
        username="lea@example.com",
        email="lea@example.com",
        first_name="Léa",
        last_name="Petit",
        birth_date="2005-01-01",
    )
    beneficiary.save()
    beneficiary = Beneficiary.objects.get(pk=beneficiary.pk)

    assert brevo_list_id_for(beneficiary) == 99
    attrs = brevo_attributes_for(beneficiary)
    assert attrs["EMAIL"] == "lea@example.com"
    assert attrs["CIVILITE"] == ["Madame"]
    assert attrs["DATE_DE_NAISSANCE"] == "2005-01-01"
    assert attrs["TYPES_DE_CONTACT"] == ["Beneficiaire TPT"]


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
def test_soft_delete_anonymizes_expected_fields_for_beneficiary(beneficiary):
    from techpourtoutes.models import Beneficiary

    original_pk = beneficiary.pk
    original_postal_code = beneficiary.postal_code
    beneficiary.legal_representative_name = "Parent Test"
    beneficiary.legal_representative_email = "parent@example.com"
    beneficiary.faveod_id = 4243
    beneficiary.save()

    beneficiary.soft_delete()
    beneficiary.refresh_from_db()

    assert not beneficiary.is_active
    assert not beneficiary.has_usable_password()
    assert beneficiary.first_name == "Prénom"
    assert beneficiary.last_name == "Nom"
    assert beneficiary.username == f"deleted_{original_pk}"
    assert beneficiary.email == f"deleted_{original_pk}@deleted.local"
    assert beneficiary.login_token_hash == ""
    assert beneficiary.login_token_expires_at is None
    assert not beneficiary.brevo_sync_enabled

    assert beneficiary.phone == ""
    assert beneficiary.faveod_id is None
    assert beneficiary.jobirl_user_id is None
    assert beneficiary.jobirl_user_token == ""

    assert isinstance(beneficiary, Beneficiary)
    assert beneficiary.birth_date is None
    assert beneficiary.postal_code == original_postal_code
    assert beneficiary.legal_representative_name == ""
    assert beneficiary.legal_representative_email == ""


@pytest.mark.django_db
def test_is_registered_for_mentoring_false_by_default(beneficiary):
    assert beneficiary.is_registered_for_mentoring is False


@pytest.mark.django_db
def test_is_registered_for_mentoring_true_for_an_adult_with_a_jobirl_account(beneficiary):
    beneficiary.jobirl_user_id = 42

    assert beneficiary.is_registered_for_mentoring is True


@pytest.mark.django_db
def test_is_registered_for_mentoring_true_for_a_minor_with_a_legal_representative(beneficiary):
    beneficiary.legal_representative_email = "parent@example.com"

    assert beneficiary.is_registered_for_mentoring is True
