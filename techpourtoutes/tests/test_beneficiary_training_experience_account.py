import re
from datetime import date

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_account_page_lists_a_card_per_beneficiary_training_experience(
    client, beneficiary, beneficiary_experience
):
    client.force_login(beneficiary)
    content = client.get(reverse("account")).content.decode()
    assert f"beneficiary-training-experience-{beneficiary_experience.pk}" in content
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
def test_beneficiary_training_experience_edit_get_prefills_form(
    client, beneficiary, beneficiary_experience
):
    client.force_login(beneficiary)
    response = client.get(
        reverse("beneficiary_training_experience_edit", args=[beneficiary_experience.pk])
    )
    assert response.status_code == 200
    assert response.context["form"].initial["course"] == "Spécialité mathématiques"


@pytest.mark.django_db
def test_beneficiary_training_experience_edit_post_updates_experience(
    client, beneficiary, beneficiary_experience, higher_ed_school
):
    client.force_login(beneficiary)

    prefix = str(beneficiary_experience.pk)
    response = client.post(
        reverse("beneficiary_training_experience_edit", args=[beneficiary_experience.pk]),
        data={
            f"{prefix}-period_label": "2024-2025",
            f"{prefix}-level": "bac_1",
            f"{prefix}-course": "Licence",
            f"{prefix}-higher_ed_school_id": str(higher_ed_school.id),
        },
    )

    assert response.status_code == 200
    beneficiary_experience.refresh_from_db()
    assert beneficiary_experience.course == "Licence"
    assert beneficiary_experience.higher_ed_school == higher_ed_school
    assert beneficiary_experience.school is None


@pytest.mark.django_db
def test_beneficiary_training_experience_cannot_be_edited_by_another_beneficiary(
    client, beneficiary_experience
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

    response = client.get(
        reverse("beneficiary_training_experience_edit", args=[beneficiary_experience.pk])
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_beneficiary_training_experience_cannot_be_edited_by_a_pro(
    client, beneficiary_experience, pro
):
    client.force_login(pro)
    response = client.get(
        reverse("beneficiary_training_experience_edit", args=[beneficiary_experience.pk])
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_beneficiary_training_experience_delete_removes_experience(
    client, beneficiary, beneficiary_experience
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

    response = client.post(
        reverse("beneficiary_training_experience_delete", args=[beneficiary_experience.pk])
    )

    assert response.status_code == 200
    assert not beneficiary.training_experiences.filter(pk=beneficiary_experience.pk).exists()


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
    client, beneficiary, beneficiary_experience
):
    from django.contrib.messages import get_messages

    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_delete", args=[beneficiary_experience.pk])
    )

    assert response.status_code == 200
    assert response["HX-Redirect"] == reverse("account")
    assert beneficiary.training_experiences.filter(pk=beneficiary_experience.pk).exists()
    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Au moins une formation doit être renseignée." in m for m in stored)


@pytest.mark.django_db
def test_beneficiary_training_experience_cannot_be_deleted_by_another_beneficiary(
    client, beneficiary_experience
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

    response = client.post(
        reverse("beneficiary_training_experience_delete", args=[beneficiary_experience.pk])
    )

    assert response.status_code == 404
    assert beneficiary_experience.user.training_experiences.filter(
        pk=beneficiary_experience.pk
    ).exists()


@pytest.mark.django_db
def test_beneficiary_training_experience_cannot_be_deleted_by_a_pro(
    client, beneficiary_experience, pro
):
    client.force_login(pro)

    response = client.post(
        reverse("beneficiary_training_experience_delete", args=[beneficiary_experience.pk])
    )

    assert response.status_code == 404
    assert beneficiary_experience.user.training_experiences.filter(
        pk=beneficiary_experience.pk
    ).exists()


@pytest.mark.django_db
def test_beneficiary_training_experience_edit_forms_have_unique_search_result_ids(
    client, beneficiary, beneficiary_experience, school
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
        reverse("beneficiary_training_experience_edit", args=[beneficiary_experience.pk])
    ).content.decode()
    second = client.get(
        reverse("beneficiary_training_experience_edit", args=[other.pk])
    ).content.decode()

    assert f'id="school-results-{beneficiary_experience.pk}"' in first
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
    client, beneficiary, beneficiary_experience
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
        data={f"{current.pk}-not_enrolled": "on"},
    )

    assert response.status_code == 200
    assert not beneficiary.training_experiences.filter(pk=current.pk).exists()
    content = response.content.decode()
    assert "Je ne suis pas inscrite dans une formation" in content
    assert re.search(r'<input[^>]*id="id_not_enrolled"[^>]*>', content) is None


@pytest.mark.django_db
def test_beneficiary_training_experience_edit_form_targets_itself_via_htmx(
    client, beneficiary, beneficiary_experience
):
    client.force_login(beneficiary)

    for response in (
        client.get(reverse("beneficiary_training_experience_add")),
        client.get(reverse("beneficiary_training_experience_add"), {"current_year": "true"}),
        client.get(
            reverse("beneficiary_training_experience_edit", args=[beneficiary_experience.pk])
        ),
    ):
        content = response.content.decode()
        assert re.search(r'<form[^>]*hx-target="this"[^>]*>', content) is not None


@pytest.mark.django_db
def test_beneficiary_training_experience_card_modifier_targets_closest_ancestor(
    client, beneficiary, beneficiary_experience
):
    client.force_login(beneficiary)

    content = client.get(reverse("account")).content.decode()

    assert "hx-target=\"closest [id^='beneficiary-training-experience-']\"" in content
    assert 'hx-target="#beneficiary-training-experience-' not in content


@pytest.mark.django_db
def test_beneficiary_training_experience_add_forms_get_distinct_prefixes(client, beneficiary):
    client.force_login(beneficiary)

    first = client.get(reverse("beneficiary_training_experience_add")).content.decode()
    second = client.get(reverse("beneficiary_training_experience_add")).content.decode()

    first_prefix = re.search(r'name="form_prefix" value="([^"]+)"', first).group(1)
    second_prefix = re.search(r'name="form_prefix" value="([^"]+)"', second).group(1)

    assert first_prefix != second_prefix
    assert f'id="id_{first_prefix}-level"' in first
    assert f'id="id_{second_prefix}-level"' in second


@pytest.mark.django_db
def test_beneficiary_training_experience_current_year_and_new_year_forms_do_not_collide(
    client, beneficiary
):
    client.force_login(beneficiary)

    current_year_content = client.get(
        reverse("beneficiary_training_experience_add"), {"current_year": "true"}
    ).content.decode()
    new_year_content = client.get(reverse("beneficiary_training_experience_add")).content.decode()

    assert 'id="id_level"' in current_year_content
    assert 'id="id_level"' not in new_year_content


@pytest.mark.django_db
def test_beneficiary_training_experience_add_invalid_post_reuses_submitted_prefix(
    client, beneficiary
):
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_add"),
        data={"form_prefix": "abc123", "period_label": "2024-2025"},
    )

    assert response.status_code == 200
    assert response.context["form"].errors
    content = response.content.decode()
    assert 'id="id_abc123-level"' in content


@pytest.mark.django_db
def test_beneficiary_training_experience_edit_forms_get_distinct_prefixes(
    client, beneficiary, beneficiary_experience, school
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
        reverse("beneficiary_training_experience_edit", args=[beneficiary_experience.pk])
    ).content.decode()
    second = client.get(
        reverse("beneficiary_training_experience_edit", args=[other.pk])
    ).content.decode()

    assert f'id="id_{beneficiary_experience.pk}-level"' in first
    assert f'id="id_{other.pk}-level"' in second
