import re
from datetime import date

import pytest
from django.test import override_settings
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
    assert response.context["form"].initial["formation_label"] == "Master Informatique"
    assert response.context["form"].initial["level"] == "bac_3"


@pytest.mark.django_db
def test_training_experience_edit_post_updates_experience(client, pro, experience):
    other = _another_school()
    ingenieur = _another_formation()
    client.force_login(pro)

    response = client.post(
        reverse("pro_training_experience_edit", args=[experience.pk]),
        data={
            "school_id": str(other.id),
            "level": "bac_5",
            "formation_id": str(ingenieur.pk),
        },
    )

    assert response.status_code == 200
    experience.refresh_from_db()
    assert experience.formation == ingenieur
    assert experience.school == other
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
    from techpourtoutes.models import School

    school = School(
        onisep_id="11", name="École polytechnique", acronym="X", uai="0911568K", higher_ed=True
    )
    school.save()
    return school


def _another_formation():
    from techpourtoutes.models import Formation

    formation = Formation(onisep_id="12", name="Diplôme d'ingénieur", higher_ed=True)
    formation.save()
    return formation


@pytest.mark.django_db
def test_account_page_lists_a_card_per_beneficiary_training_experience(
    client, beneficiary, beneficiary_experience
):
    client.force_login(beneficiary)
    content = client.get(reverse("account")).content.decode()
    assert f"beneficiary-training-experience-{beneficiary_experience.pk}" in content
    assert "Spécialité mathématiques" in content


@pytest.mark.django_db
def test_account_page_places_current_year_placeholder_after_future_experience(client, beneficiary):
    from techpourtoutes.models import Level, TrainingExperience
    from techpourtoutes.utils.school_year import next_school_year_start_date

    next_year = TrainingExperience.objects.create(
        user=beneficiary,
        level=Level.BAC_1,
        start_date=next_school_year_start_date(),
        end_date=date(next_school_year_start_date().year + 1, 8, 31),
    )
    client.force_login(beneficiary)

    content = client.get(reverse("account")).content.decode()

    assert content.index(f'id="beneficiary-training-experience-{next_year.pk}"') < content.index(
        'id="beneficiary-training-experience-current-year"'
    )


@pytest.mark.django_db
def test_beneficiary_training_experience_add_get_returns_empty_form(client, beneficiary):
    client.force_login(beneficiary)
    response = client.get(reverse("beneficiary_training_experience_add"))
    assert response.status_code == 200
    assert response.context["form"].initial == {}


@pytest.mark.django_db
def test_beneficiary_training_experience_add_post_creates_experience(
    client, beneficiary, school, formation
):
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_add"),
        data={
            "period_label": "2024-2025",
            "level": "seconde",
            "formation_id": str(formation.pk),
            "school_id": str(school.pk),
            "school_label": school.location_label,
        },
    )

    assert response.status_code == 200
    assert beneficiary.training_experiences.count() == 1
    created = beneficiary.training_experiences.get()
    assert created.school == school
    assert created.formation == formation


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_beneficiary_missing_formation_is_saved_partially_reported_and_flagged(
    client, beneficiary, school
):
    from django.core import mail

    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_add"),
        data={
            "period_label": "2024-2025",
            "level": "seconde",
            "school_id": str(school.pk),
            "school_label": school.location_label,
            "formation_id": "",
            "formation_label": "Bac pro maréchalerie",
            "formation_not_found": "on",
        },
    )

    assert response.status_code == 200
    created = beneficiary.training_experiences.get()
    assert created.school == school
    assert created.formation is None

    report = next(msg for msg in mail.outbox if msg.to == ["perfectible@techpourtoutes.io"])
    assert "Bac pro maréchalerie" in report.body
    assert "transmises à l'équipe" in response.content.decode()


@pytest.mark.django_db
def test_beneficiary_training_experience_add_post_repositions_card_before_older_experience(
    client, beneficiary, school, formation
):
    from techpourtoutes.models import Level, TrainingExperience

    older = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.SECONDE,
        start_date=date(2020, 9, 1),
        end_date=date(2021, 8, 31),
    )
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_add"),
        data={
            "period_label": "2022-2023",
            "level": "premiere",
            "formation_id": str(formation.pk),
            "school_id": str(school.pk),
            "school_label": school.location_label,
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert f'hx-swap-oob="beforebegin:#beneficiary-training-experience-{older.pk}"' in content
    created = beneficiary.training_experiences.exclude(pk=older.pk).get()
    # htmx drops the oob-carrying element itself for non-outerHTML swap styles and only
    # inserts its children, so the id must live on a nested element, not the oob element.
    id_tag_start = content.index(f'id="beneficiary-training-experience-{created.pk}"')
    id_tag_open = content.rindex("<", 0, id_tag_start)
    id_tag_close = content.index(">", id_tag_start)
    assert "hx-swap-oob" not in content[id_tag_open:id_tag_close]


@pytest.mark.django_db
def test_beneficiary_training_experience_add_post_appends_when_it_is_the_earliest(
    client, beneficiary, beneficiary_experience, school, formation
):
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_add"),
        data={
            "period_label": "2020-2021",
            "level": "seconde",
            "formation_id": str(formation.pk),
            "school_id": str(school.pk),
            "school_label": school.location_label,
        },
    )

    assert response.status_code == 200
    assert 'hx-swap-oob="beforeend:#beneficiary-training-experiences"' in response.content.decode()


@pytest.mark.django_db
def test_beneficiary_training_experience_edit_post_repositions_when_period_changes(
    client, beneficiary, beneficiary_experience, school, formation
):
    from techpourtoutes.models import Level, TrainingExperience

    older = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.SECONDE,
        start_date=date(2020, 9, 1),
        end_date=date(2021, 8, 31),
    )
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_edit", args=[beneficiary_experience.pk]),
        data={
            "period_label": "2021-2022",
            "level": "premiere",
            "formation_id": str(formation.pk),
            "school_id": str(school.pk),
            "school_label": school.location_label,
        },
    )

    assert response.status_code == 200
    assert (
        f'hx-swap-oob="beforebegin:#beneficiary-training-experience-{older.pk}"'
        in response.content.decode()
    )


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
    assert response.context["form"].initial["formation_label"] == "Spécialité mathématiques"


@pytest.mark.django_db
def test_beneficiary_training_experience_edit_post_updates_experience(
    client, beneficiary, beneficiary_experience, higher_ed_school, higher_ed_formation
):
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_edit", args=[beneficiary_experience.pk]),
        data={
            "period_label": "2024-2025",
            "level": "bac_1",
            "formation_id": str(higher_ed_formation.pk),
            "school_id": str(higher_ed_school.id),
        },
    )

    assert response.status_code == 200
    beneficiary_experience.refresh_from_db()
    assert beneficiary_experience.formation == higher_ed_formation
    assert beneficiary_experience.school == higher_ed_school


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
    from techpourtoutes.models import Level, TrainingExperience
    from techpourtoutes.utils.school_year import current_school_year_start_date

    TrainingExperience.objects.create(
        user=beneficiary,
        level=Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
    )
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_delete", args=[beneficiary_experience.pk])
    )

    assert response.status_code == 200
    assert not beneficiary.training_experiences.filter(pk=beneficiary_experience.pk).exists()


@pytest.mark.django_db
def test_beneficiary_training_experience_delete_rejects_current_school_year(client, beneficiary):
    from techpourtoutes.models import Level, TrainingExperience
    from techpourtoutes.utils.school_year import current_school_year_start_date

    current = TrainingExperience.objects.create(
        user=beneficiary,
        level=Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
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
    from techpourtoutes.models import Level, TrainingExperience

    other = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.SECONDE,
        start_date=date(2022, 9, 1),
        end_date=date(2023, 8, 31),
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
    assert f'id="formation-results-{beneficiary_experience.pk}"' in first
    assert f'id="formation-results-{other.pk}"' in second


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
    checkbox = re.search(r'<input[^>]*id="id_current-year_not_enrolled"[^>]*>', content)
    assert checkbox is not None
    assert "checked" in checkbox.group()


@pytest.mark.django_db
def test_account_page_does_not_duplicate_existing_current_year_experience(client, beneficiary):
    from techpourtoutes.models import Level, TrainingExperience
    from techpourtoutes.utils.school_year import current_school_year_start_date

    current = TrainingExperience.objects.create(
        user=beneficiary,
        level=Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
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
        reverse("beneficiary_training_experience_add") + "?current_year=true",
        data={"not_enrolled": "on"},
    )

    assert response.status_code == 200
    assert beneficiary.training_experiences.count() == 0
    content = response.content.decode()
    assert "Je ne suis pas inscrite dans une formation" in content
    assert re.search(r'<input[^>]*id="id_not_enrolled"[^>]*>', content) is None


@pytest.mark.django_db
def test_beneficiary_training_experience_add_post_current_year_creates_experience(
    client, beneficiary, school, formation
):
    from techpourtoutes.utils.school_year import current_school_year_start_date

    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_add") + "?current_year=true",
        data={
            "level": "seconde",
            "formation_id": str(formation.pk),
            "school_id": str(school.pk),
            "school_label": school.location_label,
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
    from techpourtoutes.models import Level, TrainingExperience
    from techpourtoutes.utils.school_year import current_school_year_start_date

    current = TrainingExperience.objects.create(
        user=beneficiary,
        level=Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
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
def test_beneficiary_training_experience_add_forms_get_distinct_dom_ids(client, beneficiary):
    client.force_login(beneficiary)

    first = client.get(reverse("beneficiary_training_experience_add"))
    second = client.get(reverse("beneficiary_training_experience_add"))

    first_dom_id = first.context["form"].dom_id
    second_dom_id = second.context["form"].dom_id

    assert first_dom_id != second_dom_id
    assert f'id="beneficiary-training-experience-{first_dom_id}"' in first.content.decode()
    assert f'id="id_{first_dom_id}_level"' in first.content.decode()
    assert f'id="id_{second_dom_id}_level"' in second.content.decode()


@pytest.mark.django_db
def test_beneficiary_training_experience_current_year_and_new_year_forms_do_not_collide(
    client, beneficiary
):
    client.force_login(beneficiary)

    current_year_content = client.get(
        reverse("beneficiary_training_experience_add"), {"current_year": "true"}
    ).content.decode()
    new_year_content = client.get(reverse("beneficiary_training_experience_add")).content.decode()

    assert 'id="id_current-year_level"' in current_year_content
    assert 'id="id_current-year_level"' not in new_year_content


@pytest.mark.django_db
def test_beneficiary_training_experience_add_invalid_post_rerenders_form_with_consistent_ids(
    client, beneficiary
):
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_add"),
        data={"period_label": "2024-2025"},
    )

    assert response.status_code == 200
    assert response.context["form"].errors
    dom_id = response.context["form"].dom_id
    content = response.content.decode()
    assert f'id="beneficiary-training-experience-{dom_id}"' in content
    assert f'id="id_{dom_id}_level"' in content


@pytest.mark.django_db
def test_beneficiary_training_experience_add_invalid_post_keeps_current_year_form(
    client, beneficiary
):
    client.force_login(beneficiary)

    response = client.post(
        reverse("beneficiary_training_experience_add") + "?current_year=true",
        data={"not_enrolled": ""},
    )

    assert response.status_code == 200
    form = response.context["form"]
    assert form.errors
    assert form.current_year
    assert form.dom_id == "current-year"
    assert 'id="id_current-year_not_enrolled"' in response.content.decode()


@pytest.mark.django_db
def test_beneficiary_training_experience_edit_forms_get_distinct_dom_ids(
    client, beneficiary, beneficiary_experience, school
):
    from techpourtoutes.models import Level, TrainingExperience

    other = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.SECONDE,
        start_date=date(2022, 9, 1),
        end_date=date(2023, 8, 31),
    )
    client.force_login(beneficiary)

    first = client.get(
        reverse("beneficiary_training_experience_edit", args=[beneficiary_experience.pk])
    ).content.decode()
    second = client.get(
        reverse("beneficiary_training_experience_edit", args=[other.pk])
    ).content.decode()

    assert f'id="id_{beneficiary_experience.pk}_level"' in first
    assert f'id="id_{other.pk}_level"' in second


@pytest.mark.django_db
def test_a_parcours_the_backfill_could_not_match_still_shows_its_filiere(
    client, beneficiary, school
):
    """Until `course` is dropped, an unmatched parcours keeps displaying its free text."""
    from techpourtoutes.models import Level, TrainingExperience

    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        formation=None,
        course="Spécialité mathématiques",
        level=Level.TERMINALE,
        start_date=date(2023, 9, 1),
        end_date=date(2024, 8, 31),
    )
    client.force_login(beneficiary)

    content = client.get(reverse("account")).content.decode()

    assert 'Formation : <span class="font-medium">Spécialité mathématiques</span>' in content
