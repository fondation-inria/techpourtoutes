import pytest

from techpourtoutes.forms import BeneficiaryMentoringSignUpForm


def _birth_date_for_age(age):
    from datetime import date

    today = date.today()
    return today.replace(year=today.year - age).isoformat()


@pytest.mark.django_db
def test_mentoring_signup_form_does_not_ask_for_the_birth_date_by_default():
    assert "birth_date" not in BeneficiaryMentoringSignUpForm().fields


@pytest.mark.django_db
def test_mentoring_signup_form_requires_the_birth_date_when_asked_for():
    form = BeneficiaryMentoringSignUpForm(data={"phone": "0612345678"}, needs_birth_date=True)

    assert not form.is_valid()
    assert "birth_date" in form.errors


@pytest.mark.django_db
def test_mentoring_signup_form_accepts_iso_birth_date_from_native_picker():
    form = BeneficiaryMentoringSignUpForm(
        data={"phone": "0612345678", "birth_date": _birth_date_for_age(20)},
        needs_birth_date=True,
    )

    assert form.is_valid()
    assert form.cleaned_data["birth_date"].isoformat() == _birth_date_for_age(20)


@pytest.mark.django_db
def test_mentoring_signup_form_rejects_a_birth_date_outside_the_programme_age_range():
    form = BeneficiaryMentoringSignUpForm(
        data={"phone": "0612345678", "birth_date": _birth_date_for_age(30)},
        needs_birth_date=True,
    )

    assert not form.is_valid()
    assert "birth_date" in form.errors
