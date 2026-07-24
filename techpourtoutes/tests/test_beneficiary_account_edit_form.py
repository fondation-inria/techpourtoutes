from datetime import date

import pytest


@pytest.mark.django_db
def test_form_prefills_from_beneficiary(beneficiary):
    from techpourtoutes.forms import BeneficiaryAccountEditForm

    form = BeneficiaryAccountEditForm(beneficiary=beneficiary)
    assert form.initial["first_name"] == "Jade"
    assert form.initial["last_name"] == "Petit"
    assert form.initial["birth_date"] == date(2008, 3, 15)
    assert form.initial["email"] == "jade@example.com"
    assert form.initial["phone"] == "06 12 34 56 78"


@pytest.mark.django_db
def test_form_email_field_is_disabled(beneficiary):
    from techpourtoutes.forms import BeneficiaryAccountEditForm

    form = BeneficiaryAccountEditForm(beneficiary=beneficiary)
    assert form.fields["email"].disabled


@pytest.mark.django_db
def test_form_save_updates_beneficiary(beneficiary):
    from techpourtoutes.forms import BeneficiaryAccountEditForm

    form = BeneficiaryAccountEditForm(
        data={
            "first_name": "Léa",
            "last_name": "Petit",
            "birth_date": "2008-03-15",
            "phone": "0698765432",
            "postal_code": "69001",
        }
    )
    assert form.is_valid(), form.errors
    form.save(beneficiary)

    beneficiary.refresh_from_db()
    assert beneficiary.first_name == "Léa"
    assert beneficiary.postal_code == "69001"
    assert beneficiary.phone == "+33698765432"


@pytest.mark.django_db
def test_form_rejects_invalid_postal_code():
    from techpourtoutes.forms import BeneficiaryAccountEditForm

    form = BeneficiaryAccountEditForm(
        data={
            "first_name": "Léa",
            "last_name": "Petit",
            "birth_date": "2008-03-15",
            "postal_code": "not-a-postcode",
        }
    )
    assert not form.is_valid()
    assert "postal_code" in form.errors


@pytest.mark.django_db
def test_form_rejects_missing_birth_date():
    from techpourtoutes.forms import BeneficiaryAccountEditForm

    form = BeneficiaryAccountEditForm(data={"first_name": "Léa", "last_name": "Petit"})
    assert not form.is_valid()
    assert "birth_date" in form.errors
