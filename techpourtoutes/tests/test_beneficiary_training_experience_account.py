import re
from datetime import date

import pytest
from django.urls import reverse


@pytest.fixture
def experience(beneficiary, school):
    from techpourtoutes.models import TrainingExperience

    return TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.TERMINALE,
        start_date=date(2023, 9, 1),
        end_date=date(2024, 8, 31),
        course="Spécialité mathématiques",
    )


@pytest.mark.django_db
def test_account_page_lists_a_card_per_beneficiary_training_experience(
    client, beneficiary, experience
):
    client.force_login(beneficiary)
    content = client.get(reverse("account")).content.decode()
    assert f"beneficiary-training-experience-{experience.pk}" in content
    assert "Spécialité mathématiques" in content


@pytest.mark.django_db
def test_beneficiary_training_experience_add_get_returns_empty_form(client, beneficiary):
    client.force_login(beneficiary)
    response = client.get(reverse("beneficiary_training_experience_add"))
    assert response.status_code == 200
    assert response.context["form"].initial == {}


@pytest.mark.django_db
def test_beneficiary_training_experience_add_post_creates_experience(client, beneficiary, school):
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_add"),
        data={
            "period_label": "2024-2025",
            "level": "seconde",
            "course": "Tronc commun",
            "school_identifier": school.identifier,
            "school_name": school.name,
        },
    )

    assert response.status_code == 200
    assert beneficiary.training_experiences.count() == 1
    created = beneficiary.training_experiences.get()
    assert created.school == school
    assert created.course == "Tronc commun"


@pytest.mark.django_db
def test_beneficiary_training_experience_add_requires_beneficiary_account(client, pro):
    client.force_login(pro)
    response = client.get(reverse("beneficiary_training_experience_add"))
    assert response.status_code == 404


@pytest.mark.django_db
def test_beneficiary_training_experience_edit_get_prefills_form(client, beneficiary, experience):
    client.force_login(beneficiary)
    response = client.get(reverse("beneficiary_training_experience_edit", args=[experience.pk]))
    assert response.status_code == 200
    assert response.context["form"].initial["course"] == "Spécialité mathématiques"


@pytest.mark.django_db
def test_beneficiary_training_experience_edit_post_updates_experience(
    client, beneficiary, experience, higher_ed_school
):
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_edit", args=[experience.pk]),
        data={
            "period_label": "2024-2025",
            "level": "bac_1",
            "course": "Licence",
            "higher_ed_school_id": str(higher_ed_school.id),
        },
    )

    assert response.status_code == 200
    experience.refresh_from_db()
    assert experience.course == "Licence"
    assert experience.higher_ed_school == higher_ed_school
    assert experience.school is None


@pytest.mark.django_db
def test_beneficiary_training_experience_cannot_be_edited_by_another_beneficiary(
    client, experience
):
    from datetime import date

    from techpourtoutes.models import Beneficiary

    intruder = Beneficiary(
        username="eve@example.com",
        first_name="Eve",
        last_name="X",
        email="eve@example.com",
        birth_date=date(2007, 1, 1),
    )
    intruder.save()
    client.force_login(intruder)

    response = client.get(reverse("beneficiary_training_experience_edit", args=[experience.pk]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_beneficiary_training_experience_cannot_be_edited_by_a_pro(client, experience, pro):
    client.force_login(pro)
    response = client.get(reverse("beneficiary_training_experience_edit", args=[experience.pk]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_beneficiary_training_experience_delete_removes_experience(
    client, beneficiary, experience
):
    from techpourtoutes.models import TrainingExperience
    from techpourtoutes.models.training_experience import current_school_year_start_date

    TrainingExperience.objects.create(
        user=beneficiary,
        level=TrainingExperience.Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
        course="Terminale",
    )
    client.force_login(beneficiary)

    response = client.post(reverse("beneficiary_training_experience_delete", args=[experience.pk]))

    assert response.status_code == 200
    assert not beneficiary.training_experiences.filter(pk=experience.pk).exists()


@pytest.mark.django_db
def test_beneficiary_training_experience_delete_rejects_current_school_year(client, beneficiary):
    from techpourtoutes.models import TrainingExperience
    from techpourtoutes.models.training_experience import current_school_year_start_date

    current = TrainingExperience.objects.create(
        user=beneficiary,
        level=TrainingExperience.Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
        course="Terminale",
    )
    client.force_login(beneficiary)

    response = client.post(reverse("beneficiary_training_experience_delete", args=[current.pk]))

    assert response.status_code == 403
    assert beneficiary.training_experiences.filter(pk=current.pk).exists()


@pytest.mark.django_db
def test_beneficiary_training_experience_delete_rejects_last_remaining_experience(
    client, beneficiary, experience
):
    from django.contrib.messages import get_messages

    client.force_login(beneficiary)

    response = client.post(reverse("beneficiary_training_experience_delete", args=[experience.pk]))

    assert response.status_code == 200
    assert response["HX-Redirect"] == reverse("account")
    assert beneficiary.training_experiences.filter(pk=experience.pk).exists()
    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Au moins une formation doit être renseignée." in m for m in stored)


@pytest.mark.django_db
def test_beneficiary_training_experience_cannot_be_deleted_by_another_beneficiary(
    client, experience
):
    from datetime import date

    from techpourtoutes.models import Beneficiary

    intruder = Beneficiary(
        username="eve@example.com",
        first_name="Eve",
        last_name="X",
        email="eve@example.com",
        birth_date=date(2007, 1, 1),
    )
    intruder.save()
    client.force_login(intruder)

    response = client.post(reverse("beneficiary_training_experience_delete", args=[experience.pk]))

    assert response.status_code == 404
    assert experience.user.training_experiences.filter(pk=experience.pk).exists()


@pytest.mark.django_db
def test_beneficiary_training_experience_cannot_be_deleted_by_a_pro(client, experience, pro):
    client.force_login(pro)

    response = client.post(reverse("beneficiary_training_experience_delete", args=[experience.pk]))

    assert response.status_code == 404
    assert experience.user.training_experiences.filter(pk=experience.pk).exists()


@pytest.mark.django_db
def test_beneficiary_training_experience_edit_forms_have_unique_search_result_ids(
    client, beneficiary, experience, school
):
    from techpourtoutes.models import TrainingExperience

    other = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.SECONDE,
        start_date=date(2022, 9, 1),
        end_date=date(2023, 8, 31),
        course="Tronc commun",
    )
    client.force_login(beneficiary)

    first = client.get(
        reverse("beneficiary_training_experience_edit", args=[experience.pk])
    ).content.decode()
    second = client.get(
        reverse("beneficiary_training_experience_edit", args=[other.pk])
    ).content.decode()

    assert f'id="school-results-{experience.pk}"' in first
    assert f'id="school-results-{other.pk}"' in second


@pytest.mark.django_db
def test_account_page_shows_not_enrolled_status_when_no_current_year_experience(
    client, beneficiary
):
    client.force_login(beneficiary)

    content = client.get(reverse("account")).content.decode()

    assert "Je ne suis pas inscrite dans une formation" in content
    assert re.search(r'<input[^>]*id="id_not_enrolled"[^>]*>', content) is None


@pytest.mark.django_db
def test_beneficiary_training_experience_add_get_current_year_returns_checked_form(
    client, beneficiary
):
    client.force_login(beneficiary)

    response = client.get(reverse("beneficiary_training_experience_add"), {"current_year": "true"})

    assert response.status_code == 200
    content = response.content.decode()
    checkbox = re.search(r'<input[^>]*id="id_not_enrolled"[^>]*>', content)
    assert checkbox is not None
    assert "checked" in checkbox.group()


@pytest.mark.django_db
def test_account_page_does_not_duplicate_existing_current_year_experience(client, beneficiary):
    from techpourtoutes.models import TrainingExperience
    from techpourtoutes.models.training_experience import current_school_year_start_date

    current = TrainingExperience.objects.create(
        user=beneficiary,
        level=TrainingExperience.Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
        course="Terminale",
    )
    client.force_login(beneficiary)

    content = client.get(reverse("account")).content.decode()

    assert content.count(f'id="beneficiary-training-experience-{current.pk}"') == 1
    assert re.search(r'<input[^>]*id="id_not_enrolled"[^>]*>', content) is None


@pytest.mark.django_db
def test_beneficiary_training_experience_add_post_current_year_not_enrolled_creates_nothing(
    client, beneficiary
):
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_add"),
        data={"not_enrolled": "on", "current_year": "true"},
    )

    assert response.status_code == 200
    assert beneficiary.training_experiences.count() == 0
    content = response.content.decode()
    assert "Je ne suis pas inscrite dans une formation" in content
    assert re.search(r'<input[^>]*id="id_not_enrolled"[^>]*>', content) is None


@pytest.mark.django_db
def test_beneficiary_training_experience_add_post_current_year_creates_experience(
    client, beneficiary, school
):
    from techpourtoutes.models.training_experience import current_school_year_start_date

    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_add"),
        data={
            "level": "seconde",
            "course": "Tronc commun",
            "school_identifier": school.identifier,
            "school_name": school.name,
            "current_year": "true",
        },
    )

    assert response.status_code == 200
    assert beneficiary.training_experiences.count() == 1
    created = beneficiary.training_experiences.get()
    assert created.start_date == current_school_year_start_date()
    assert created.school == school


@pytest.mark.django_db
def test_beneficiary_training_experience_edit_post_not_enrolled_deletes_current_year_experience(
    client, beneficiary, experience
):
    from techpourtoutes.models import TrainingExperience
    from techpourtoutes.models.training_experience import current_school_year_start_date

    current = TrainingExperience.objects.create(
        user=beneficiary,
        level=TrainingExperience.Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
        course="Terminale",
    )
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_edit", args=[current.pk]),
        data={"not_enrolled": "on"},
    )

    assert response.status_code == 200
    assert not beneficiary.training_experiences.filter(pk=current.pk).exists()
    content = response.content.decode()
    assert "Je ne suis pas inscrite dans une formation" in content
    assert re.search(r'<input[^>]*id="id_not_enrolled"[^>]*>', content) is None
