import pytest
from django.test import override_settings

from techpourtoutes.models import Beneficiary, User
from techpourtoutes.services.brevo_api.mappings import brevo_attributes_for, brevo_list_id_for


@pytest.mark.django_db
def test_beneficiary_creation_is_passwordless_and_madame():
    beneficiary = Beneficiary(username="lea@example.com", email="lea@example.com")
    beneficiary.save()

    assert not beneficiary.has_usable_password()
    assert beneficiary.civility == User.Civility.MADAME


@pytest.mark.django_db
def test_personal_fields_live_on_user():
    beneficiary = Beneficiary(username="lea@example.com", email="lea@example.com")
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
