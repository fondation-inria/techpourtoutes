from datetime import date

import pytest


@pytest.mark.django_db
def test_form_prefills_from_experience_with_school(beneficiary_experience, school, formation):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(experience=beneficiary_experience)
    assert form.initial["level"] == "terminale"
    assert form.initial["period_label"] == "2023-2024"
    assert form.initial["formation_id"] == str(formation.pk)
    assert form.initial["formation_label"] == "Spécialité mathématiques"
    assert form.initial["school_id"] == str(school.pk)
    # A secondary school is offered with its postal code, and comes back the same way.
    assert form.initial["school_label"] == school.location_label


@pytest.mark.django_db
def test_form_prefills_from_experience_with_higher_ed_school(beneficiary, higher_ed_school):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import Level, TrainingExperience

    experience = TrainingExperience.objects.create(
        user=beneficiary,
        school=higher_ed_school,
        level=Level.BAC_1,
        start_date=date(2023, 9, 1),
        end_date=date(2024, 8, 31),
    )

    form = BeneficiaryTrainingExperienceForm(experience=experience)
    assert form.initial["school_id"] == str(higher_ed_school.id)
    assert form.initial["school_label"] == higher_ed_school.display_label


@pytest.mark.django_db
def test_form_locks_period_label_for_current_school_year_experience(
    beneficiary, school, formation
):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import Level, TrainingExperience
    from techpourtoutes.utils.school_year import current_school_year_start_date

    current = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
    )

    form = BeneficiaryTrainingExperienceForm(experience=current)
    assert form.fields["period_label"].disabled

    form = BeneficiaryTrainingExperienceForm(
        experience=current,
        data={
            "period_label": "2000-2001",
            "level": "terminale",
            "formation_id": str(formation.pk),
            "school_id": str(school.pk),
            "school_label": school.location_label,
        },
    )
    assert form.is_valid(), form.errors
    saved = form.save(current)

    assert saved.start_date == current_school_year_start_date()


@pytest.mark.django_db
def test_form_rejects_duplicate_period_label_for_same_beneficiary(beneficiary, school, formation):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import Level, TrainingExperience

    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.TERMINALE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
    )

    form = BeneficiaryTrainingExperienceForm(
        beneficiary=beneficiary,
        data={
            "period_label": "2024-2025",
            "level": "premiere",
            "formation_id": str(formation.pk),
            "school_id": str(school.pk),
            "school_label": school.location_label,
        },
    )

    assert not form.is_valid()
    assert "period_label" in form.errors


@pytest.mark.django_db
def test_form_allows_keeping_own_period_label_when_editing(beneficiary, school, formation):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import Level, TrainingExperience

    experience = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.TERMINALE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
    )

    form = BeneficiaryTrainingExperienceForm(
        experience=experience,
        data={
            "period_label": "2024-2025",
            "level": "terminale",
            "formation_id": str(formation.pk),
            "school_id": str(school.pk),
            "school_label": school.location_label,
        },
    )

    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_form_valid_when_not_enrolled_for_current_year_without_level_formation_or_school(
    beneficiary,
):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(
        beneficiary=beneficiary,
        current_year=True,
        data={"not_enrolled": "on"},
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["not_enrolled"] is True


@pytest.mark.django_db
def test_form_still_requires_a_level_when_not_not_enrolled():
    """Without a level there is no perimeter, so neither school nor formation resolves."""
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(data={"period_label": "2024-2025"})

    assert not form.is_valid()
    assert "level" in form.errors


@pytest.mark.django_db
def test_form_requires_a_formation_once_the_school_is_known(school, formation):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(
        data={
            "period_label": "2024-2025",
            "level": "terminale",
            "school_id": str(school.pk),
            "school_label": school.location_label,
        }
    )

    assert not form.is_valid()
    assert "formation_id" in form.errors


@pytest.mark.django_db
def test_form_rejects_a_formation_the_school_does_not_teach(school, formation):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import Formation

    elsewhere = Formation(onisep_id="9999", name="Diplôme d'ingénieur")
    elsewhere.save()

    form = BeneficiaryTrainingExperienceForm(
        data={
            "period_label": "2024-2025",
            "level": "terminale",
            "school_id": str(school.pk),
            "school_label": school.location_label,
            "formation_id": str(elsewhere.pk),
        }
    )

    assert not form.is_valid()
    assert "formation_id" in form.errors


@pytest.mark.django_db
def test_form_reports_the_school_before_the_formation(school, formation):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(
        data={
            "period_label": "2024-2025",
            "level": "terminale",
            "school_id": "not-a-real-identifier",
            "formation_id": str(formation.pk),
        }
    )

    assert "school_id" in form.errors
    assert "formation_id" not in form.errors


@pytest.mark.django_db
def test_a_missing_formation_keeps_the_school_and_saves_nothing_else(beneficiary, school):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import TrainingExperience

    form = BeneficiaryTrainingExperienceForm(
        data={
            "period_label": "2024-2025",
            "level": "terminale",
            "school_id": str(school.pk),
            "school_label": school.location_label,
            "formation_id": "",
            "formation_label": "Bac pro maréchalerie",
            "formation_not_found": "on",
        },
        beneficiary=beneficiary,
    )
    assert form.is_valid(), form.errors

    experience = form.save(TrainingExperience(user=beneficiary))

    assert experience.school == school
    assert experience.formation is None
    assert form.has_missing_record


@pytest.mark.django_db
def test_form_has_no_not_enrolled_field_when_not_current_year(beneficiary):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(beneficiary=beneficiary)

    assert "not_enrolled" not in form.fields


@pytest.mark.django_db
def test_form_period_label_choices_exclude_current_school_year_when_not_current_year(
    beneficiary,
):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.utils.school_year import current_school_year_label

    form = BeneficiaryTrainingExperienceForm(beneficiary=beneficiary)

    values = [value for value, _ in form.fields["period_label"].choices]
    assert current_school_year_label() not in values


@pytest.mark.django_db
def test_form_for_current_year_without_experience_locks_period_label_and_defaults_checked(
    beneficiary,
):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.utils.school_year import current_school_year_label

    form = BeneficiaryTrainingExperienceForm(beneficiary=beneficiary, current_year=True)

    assert form.fields["period_label"].disabled
    assert form.initial["period_label"] == current_school_year_label()
    assert form.fields["not_enrolled"].initial is True


@pytest.mark.django_db
def test_form_for_current_year_creates_experience_when_not_enrolled_is_unchecked(
    beneficiary, school, formation
):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import TrainingExperience
    from techpourtoutes.utils.school_year import current_school_year_start_date

    form = BeneficiaryTrainingExperienceForm(
        beneficiary=beneficiary,
        current_year=True,
        data={
            "level": "seconde",
            "formation_id": str(formation.pk),
            "school_id": str(school.pk),
            "school_label": school.location_label,
        },
    )
    assert form.is_valid(), form.errors

    experience = form.save(TrainingExperience(user=beneficiary))
    experience.refresh_from_db()
    assert experience.start_date == current_school_year_start_date()
    assert experience.school == school


@pytest.mark.django_db
def test_form_rejects_secondary_level_without_school():
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(
        data={"period_label": "2024-2025", "level": "terminale"}
    )
    assert not form.is_valid()
    assert "school_id" in form.errors


@pytest.mark.django_db
def test_form_rejects_bac_plus_level_without_higher_ed_school():
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(data={"period_label": "2024-2025", "level": "bac_1"})
    assert not form.is_valid()
    assert "school_id" in form.errors


@pytest.mark.django_db
def test_form_rejects_unknown_school_identifier():
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(
        data={
            "period_label": "2024-2025",
            "level": "terminale",
            "school_id": "not-a-real-identifier",
        }
    )
    assert not form.is_valid()
    assert "school_id" in form.errors
