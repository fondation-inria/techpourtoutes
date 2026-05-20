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
def test_mentor_form_structure_name_required_when_working(valid_mentor_data):
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data={**valid_mentor_data, "structure_name": ""})
    assert not form.is_valid()
    assert "structure_name" in form.errors


@pytest.mark.django_db
def test_mentor_form_structure_name_not_required_when_retired(valid_mentor_data):
    from techpourtoutes.forms import MentorForm

    data = {
        **valid_mentor_data,
        "professional_situation": "retired",
        "structure_name": "",
    }
    form = MentorForm(data=data)
    assert form.is_valid(), form.errors
