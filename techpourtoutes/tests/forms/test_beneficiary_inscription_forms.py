import pytest

from techpourtoutes.forms import BeneficiaryIdentityForm


@pytest.mark.django_db
def test_identity_form_accepts_iso_birth_date_from_native_picker():
    form = BeneficiaryIdentityForm(
        data={
            "first_name": "A",
            "last_name": "B",
            "birth_date": "2005-01-01",
            "age_eligibility_accepted": "on",
            "terms_accepted": "on",
        }
    )
    assert form.is_valid()
    assert form.cleaned_data["birth_date"].isoformat() == "2005-01-01"


@pytest.mark.django_db
def test_identity_form_requires_eligibility_and_terms():
    form = BeneficiaryIdentityForm(
        data={"first_name": "A", "last_name": "B", "birth_date": "01/01/2005"}
    )
    assert not form.is_valid()
    assert "age_eligibility_accepted" in form.errors
    assert "terms_accepted" in form.errors
