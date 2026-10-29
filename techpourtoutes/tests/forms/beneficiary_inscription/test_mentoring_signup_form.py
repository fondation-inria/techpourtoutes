import pytest

from techpourtoutes.forms import BeneficiaryMentoringSignUpForm
from techpourtoutes.forms.fields import INVALID_PHONE_NUMBER_MESSAGE


@pytest.mark.django_db
def test_mentoring_signup_form_rejects_an_invalid_phone_with_the_site_wide_message():
    form = BeneficiaryMentoringSignUpForm(data={"phone": "pas un numéro"})

    assert not form.is_valid()
    assert form.errors["phone"] == [INVALID_PHONE_NUMBER_MESSAGE]


def test_mentoring_signup_form_rejects_an_invalid_postal_code():
    form = BeneficiaryMentoringSignUpForm(data={"phone": "0612345678", "postal_code": "2920"})

    assert not form.is_valid()
    assert "postal_code" in form.errors


def test_mentoring_signup_form_requires_the_postal_code_it_asks():
    form = BeneficiaryMentoringSignUpForm(data={"phone": "0612345678"}, asks_postal_code=True)

    assert not form.is_valid()
    assert form.errors["postal_code"] == ["Indique ton code postal."]
