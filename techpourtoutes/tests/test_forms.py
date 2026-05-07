import pytest


@pytest.mark.django_db
def test_mentor_form_valid(valid_mentor_data):
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data=valid_mentor_data)
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_mentor_form_missing_required_field(valid_mentor_data):
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data={**valid_mentor_data, "phone": ""})
    assert not form.is_valid()
    assert "phone" in form.errors


@pytest.mark.django_db
def test_mentor_form_duplicate_email(valid_mentor_data):
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data=valid_mentor_data)
    assert form.is_valid()
    form.save()

    form2 = MentorForm(data=valid_mentor_data)
    assert not form2.is_valid()
    assert "email" in form2.errors


@pytest.mark.django_db
def test_mentor_form_save_creates_mentor(valid_mentor_data):
    from techpourtoutes.forms import MentorForm
    from techpourtoutes.models import Mentor

    form = MentorForm(data=valid_mentor_data)
    assert form.is_valid()
    mentor = form.save()
    assert isinstance(mentor, Mentor)
    assert Mentor.objects.filter(email=valid_mentor_data["email"]).exists()


@pytest.mark.django_db
def test_mentor_form_invalid_professional_situation(valid_mentor_data):
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data={**valid_mentor_data, "professional_situation": "not-a-choice"})
    assert not form.is_valid()
    assert "professional_situation" in form.errors


@pytest.mark.django_db
def test_mentor_form_blank_professional_situation(valid_mentor_data):
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data={**valid_mentor_data, "professional_situation": ""})
    assert not form.is_valid()
    assert "professional_situation" in form.errors


@pytest.mark.django_db
def test_mentor_form_requires_terms_accepted(valid_mentor_data):
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data={**valid_mentor_data, "terms_accepted": False})
    assert not form.is_valid()
    assert "terms_accepted" in form.errors


@pytest.mark.django_db
def test_mentor_form_invalid_civility(valid_mentor_data):
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data={**valid_mentor_data, "civility": "Mademoiselle"})
    assert not form.is_valid()
    assert "civility" in form.errors


@pytest.mark.django_db
def test_mentor_form_birth_date_accepts_french_format(valid_mentor_data):
    import datetime

    from techpourtoutes.forms import MentorForm

    form = MentorForm(data={**valid_mentor_data, "birth_date": "15/06/1990"})
    assert form.is_valid(), form.errors
    assert form.cleaned_data["birth_date"] == datetime.date(1990, 6, 15)
