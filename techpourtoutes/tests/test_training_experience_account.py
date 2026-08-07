import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_account_page_lists_a_card_per_training_experience(client, pro, experience):
    client.force_login(pro)
    content = client.get(reverse("account")).content.decode()
    assert f"training-experience-{experience.pk}" in content
    assert "Master Informatique" in content
    assert "Bac +3" in content
    assert "2019-2020" in content


@pytest.mark.django_db
def test_training_experience_edit_get_prefills_form(client, pro, experience):
    client.force_login(pro)
    response = client.get(reverse("pro_training_experience_edit", args=[experience.pk]))
    assert response.status_code == 200
    assert response.context["form"].initial["course"] == "Master Informatique"
    assert response.context["form"].initial["level"] == "bac_3"


@pytest.mark.django_db
def test_training_experience_edit_post_updates_experience(client, pro, experience):
    other = _another_school()
    client.force_login(pro)

    response = client.post(
        reverse("pro_training_experience_edit", args=[experience.pk]),
        data={"higher_ed_school_id": str(other.id), "level": "bac_5", "course": "Doctorat"},
    )

    assert response.status_code == 200
    experience.refresh_from_db()
    assert experience.course == "Doctorat"
    assert experience.higher_ed_school == other
    assert experience.level == "bac_5"


@pytest.mark.django_db
def test_training_experience_cannot_be_edited_by_another_pro(client, experience):
    from techpourtoutes.models import Pro

    intruder = Pro(
        username="eve@example.com",
        email="eve@example.com",
        first_name="Eve",
        last_name="Intruder",
        civility="Madame",
        professional_situation="student",
        job_title="Étudiante",
    )
    intruder.save()
    client.force_login(intruder)

    response = client.get(reverse("pro_training_experience_edit", args=[experience.pk]))
    assert response.status_code == 404


def _another_school():
    from techpourtoutes.models import HigherEdSchool

    school = HigherEdSchool(full_name="École polytechnique", name="X", uai="0911568K")
    school.save()
    return school
