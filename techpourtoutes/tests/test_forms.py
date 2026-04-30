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
