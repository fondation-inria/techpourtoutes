import uuid

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

VALID_MENTOR_DATA = {
    "first_name": "Marie",
    "last_name": "Dupont",
    "email": "marie.dupont@example.com",
    "phone": "0612345678",
    "professional_situation": "Ingénieure logiciel",
    "structure_name": "Tech Corp",
    "job_title": "Développeuse backend",
    "postal_code": "75011",
}


# --- Model tests ---


@pytest.mark.django_db
def test_user_has_uuid_pk():
    from techpourtoutes.models import User

    user = User.objects.create_user(username="test@example.com", email="test@example.com")
    assert isinstance(user.pk, uuid.UUID)


@pytest.mark.django_db
def test_mentor_inherits_user():
    from techpourtoutes.models import Mentor, User

    assert issubclass(Mentor, User)


@pytest.mark.django_db
def test_mentor_save_sets_unusable_password():
    from techpourtoutes.models import Mentor

    mentor = Mentor(username="marie.dupont@example.com", **VALID_MENTOR_DATA)
    mentor.save()
    assert not mentor.has_usable_password()


@pytest.mark.django_db
def test_mentor_creation_saves_all_fields():
    from techpourtoutes.models import Mentor

    Mentor(username="marie.dupont@example.com", **VALID_MENTOR_DATA).save()

    saved = Mentor.objects.get(email="marie.dupont@example.com")
    assert saved.first_name == "Marie"
    assert saved.phone.national_number == 612345678
    assert saved.job_title == "Développeuse backend"
    assert saved.structure_name == "Tech Corp"
    assert saved.postal_code == "75011"


@pytest.mark.django_db
def test_mentor_structure_name_optional():
    from techpourtoutes.models import Mentor

    data = {**VALID_MENTOR_DATA, "email": "autre@example.com", "structure_name": ""}
    Mentor(username="autre@example.com", **data).save()
    assert Mentor.objects.filter(email="autre@example.com").exists()


@pytest.mark.django_db
def test_mentor_save_raises_if_invalid():
    from techpourtoutes.models import Mentor

    mentor = Mentor(username="bad@example.com", **{**VALID_MENTOR_DATA, "email": "not-an-email"})
    with pytest.raises(ValidationError):
        mentor.save()


# --- Form tests ---


@pytest.mark.django_db
def test_mentor_form_valid():
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data=VALID_MENTOR_DATA)
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_mentor_form_missing_required_field():
    from techpourtoutes.forms import MentorForm

    data = {**VALID_MENTOR_DATA, "phone": ""}
    form = MentorForm(data=data)
    assert not form.is_valid()
    assert "phone" in form.errors


@pytest.mark.django_db
def test_mentor_form_duplicate_email():
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data=VALID_MENTOR_DATA)
    assert form.is_valid()
    form.save()

    form2 = MentorForm(data=VALID_MENTOR_DATA)
    assert not form2.is_valid()
    assert "email" in form2.errors


@pytest.mark.django_db
def test_mentor_form_save_creates_mentor():
    from techpourtoutes.forms import MentorForm
    from techpourtoutes.models import Mentor

    form = MentorForm(data=VALID_MENTOR_DATA)
    assert form.is_valid()
    mentor = form.save()
    assert isinstance(mentor, Mentor)
    assert Mentor.objects.filter(email=VALID_MENTOR_DATA["email"]).exists()


# --- View tests ---


@pytest.mark.django_db
def test_mentor_landing_get(client):
    url = reverse("mentor_landing")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_mentor_landing_post_valid_redirects(client):
    url = reverse("mentor_landing")
    response = client.post(url, data=VALID_MENTOR_DATA)
    assert response.status_code == 302
    assert response["Location"] == reverse("mentor_success")


@pytest.mark.django_db
def test_mentor_landing_post_invalid_rerenders_with_errors(client):
    url = reverse("mentor_landing")
    response = client.post(url, data={**VALID_MENTOR_DATA, "email": ""})
    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_mentor_landing_post_duplicate_email_shows_error(client):
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data=VALID_MENTOR_DATA)
    assert form.is_valid()
    form.save()

    url = reverse("mentor_landing")
    response = client.post(url, data=VALID_MENTOR_DATA)
    assert response.status_code == 200
    assert "form" in response.context
    assert response.context["form"].errors


@pytest.mark.django_db
def test_mentor_success_get(client):
    url = reverse("mentor_success")
    response = client.get(url)
    assert response.status_code == 200
