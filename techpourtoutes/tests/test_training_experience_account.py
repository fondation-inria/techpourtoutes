import pytest
from django.urls import reverse


@pytest.fixture
def experience(pro, higher_ed_school):
    from techpourtoutes.models import TrainingExperience

    return TrainingExperience.objects.create(
        pro=pro, higher_ed_school=higher_ed_school, course="Master Informatique"
    )


@pytest.mark.django_db
def test_account_page_lists_a_card_per_training_experience(client, pro, experience):
    client.force_login(pro)
    content = client.get(reverse("account")).content.decode()
    assert f"training-experience-{experience.pk}" in content
    assert "Master Informatique" in content


@pytest.mark.django_db
def test_training_experience_edit_get_prefills_form(client, pro, experience):
    client.force_login(pro)
    response = client.get(reverse("training_experience_edit", args=[experience.pk]))
    assert response.status_code == 200
    assert response.context["form"].initial["course"] == "Master Informatique"


@pytest.mark.django_db
def test_training_experience_edit_post_updates_experience(client, pro, experience):
    other = _another_school()
    client.force_login(pro)

    response = client.post(
        reverse("training_experience_edit", args=[experience.pk]),
        data={"higher_ed_school_id": str(other.id), "course": "Doctorat"},
    )

    assert response.status_code == 200
    experience.refresh_from_db()
    assert experience.course == "Doctorat"
    assert experience.higher_ed_school == other


@pytest.mark.django_db
def test_training_experience_cannot_be_edited_by_another_pro(client, experience):
    from techpourtoutes.models import Pro

    intruder = Pro(
        username="eve@example.com",
        email="eve@example.com",
        civility="Madame",
        professional_situation="student",
        job_title="Étudiante",
    )
    intruder.save()
    client.force_login(intruder)

    response = client.get(reverse("training_experience_edit", args=[experience.pk]))
    assert response.status_code == 404


def _another_school():
    from techpourtoutes.models import HigherEdSchool

    school = HigherEdSchool(full_name="École polytechnique", name="X", uai="0911568K")
    school.save()
    return school
