import pytest

from techpourtoutes.forms import BeneficiaryMentoringSignUpForm
from techpourtoutes.forms.fields import INVALID_PHONE_NUMBER_MESSAGE


@pytest.mark.django_db
def test_mentoring_signup_form_rejects_an_invalid_phone_with_the_site_wide_message():
    form = BeneficiaryMentoringSignUpForm(data={"phone": "pas un numéro"})

    assert not form.is_valid()
    assert form.errors["phone"] == [INVALID_PHONE_NUMBER_MESSAGE]
