from datetime import date

import pytest


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
def test_form_prefills_from_experience_with_school(experience, school):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(experience=experience)
    assert form.initial["level"] == "terminale"
    assert form.initial["period_label"] == "2023-2024"
    assert form.initial["course"] == "Spécialité mathématiques"
    assert form.initial["school_identifier"] == school.identifier
    assert form.initial["school_name"] == school.name


@pytest.mark.django_db
def test_form_prefills_from_experience_with_higher_ed_school(beneficiary, higher_ed_school):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience.objects.create(
        user=beneficiary,
        higher_ed_school=higher_ed_school,
        level=TrainingExperience.Level.BAC_1,
        start_date=date(2023, 9, 1),
        end_date=date(2024, 8, 31),
        course="Licence informatique",
    )

    form = BeneficiaryTrainingExperienceForm(experience=experience)
    assert form.initial["higher_ed_school_id"] == str(higher_ed_school.id)
    assert form.initial["higher_ed_school_label"] == higher_ed_school.display_label


@pytest.mark.django_db
def test_form_locks_period_label_for_current_school_year_experience(beneficiary, school):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import TrainingExperience
    from techpourtoutes.models.training_experience import current_school_year_start_date

    current = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
        course="Terminale",
    )

    form = BeneficiaryTrainingExperienceForm(experience=current)
    assert form.fields["period_label"].disabled

    form = BeneficiaryTrainingExperienceForm(
        experience=current,
        data={
            "period_label": "2000-2001",
            "level": "terminale",
            "course": "Terminale modifiée",
            "school_identifier": school.identifier,
            "school_name": school.name,
        },
    )
    assert form.is_valid(), form.errors
    saved = form.save(current)

    assert saved.start_date == current_school_year_start_date()


@pytest.mark.django_db
def test_form_rejects_duplicate_period_label_for_same_beneficiary(beneficiary, school):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import TrainingExperience

    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.TERMINALE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        course="Terminale",
    )

    form = BeneficiaryTrainingExperienceForm(
        beneficiary=beneficiary,
        data={
            "period_label": "2024-2025",
            "level": "premiere",
            "course": "Première",
            "school_identifier": school.identifier,
            "school_name": school.name,
        },
    )

    assert not form.is_valid()
    assert "period_label" in form.errors


@pytest.mark.django_db
def test_form_allows_keeping_own_period_label_when_editing(beneficiary, school):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=TrainingExperience.Level.TERMINALE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        course="Terminale",
    )

    form = BeneficiaryTrainingExperienceForm(
        experience=experience,
        data={
            "period_label": "2024-2025",
            "level": "terminale",
            "course": "Terminale modifiée",
            "school_identifier": school.identifier,
            "school_name": school.name,
        },
    )

    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_form_valid_when_not_enrolled_for_current_year_without_level_course_or_school(
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
def test_form_still_requires_level_and_course_when_not_not_enrolled():
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(data={"period_label": "2024-2025"})

    assert not form.is_valid()
    assert "level" in form.errors
    assert "course" in form.errors


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
    from techpourtoutes.models.training_experience import current_school_year_label

    form = BeneficiaryTrainingExperienceForm(beneficiary=beneficiary)

    values = [value for value, _ in form.fields["period_label"].choices]
    assert current_school_year_label() not in values


@pytest.mark.django_db
def test_form_for_current_year_without_experience_locks_period_label_and_defaults_checked(
    beneficiary,
):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models.training_experience import current_school_year_label

    form = BeneficiaryTrainingExperienceForm(beneficiary=beneficiary, current_year=True)

    assert form.fields["period_label"].disabled
    assert form.initial["period_label"] == current_school_year_label()
    assert form.fields["not_enrolled"].initial is True


@pytest.mark.django_db
def test_form_for_current_year_creates_experience_when_not_enrolled_is_unchecked(
    beneficiary, school
):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import TrainingExperience
    from techpourtoutes.models.training_experience import current_school_year_start_date

    form = BeneficiaryTrainingExperienceForm(
        beneficiary=beneficiary,
        current_year=True,
        data={
            "level": "seconde",
            "course": "Tronc commun",
            "school_identifier": school.identifier,
            "school_name": school.name,
        },
    )
    assert form.is_valid(), form.errors

    experience = form.save(TrainingExperience(user=beneficiary))
    experience.refresh_from_db()
    assert experience.start_date == current_school_year_start_date()
    assert experience.school == school


@pytest.mark.django_db
def test_form_save_creates_experience_with_school_for_secondary_level(beneficiary, school):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import TrainingExperience

    form = BeneficiaryTrainingExperienceForm(
        data={
            "period_label": "2024-2025",
            "level": "terminale",
            "course": "Spécialité SVT",
            "school_identifier": school.identifier,
            "school_name": school.name,
        }
    )
    assert form.is_valid(), form.errors
    experience = form.save(TrainingExperience(user=beneficiary))

    experience.refresh_from_db()
    assert experience.school == school
    assert experience.higher_ed_school is None
    assert experience.level == "terminale"


@pytest.mark.django_db
def test_form_save_creates_experience_with_higher_ed_school_for_bac_plus_level(
    beneficiary, higher_ed_school
):
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm
    from techpourtoutes.models import TrainingExperience

    form = BeneficiaryTrainingExperienceForm(
        data={
            "period_label": "2024-2025",
            "level": "bac_1",
            "course": "Licence informatique",
            "higher_ed_school_id": str(higher_ed_school.id),
        }
    )
    assert form.is_valid(), form.errors
    experience = form.save(TrainingExperience(user=beneficiary))

    experience.refresh_from_db()
    assert experience.higher_ed_school == higher_ed_school
    assert experience.school is None


@pytest.mark.django_db
def test_form_rejects_secondary_level_without_school():
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(
        data={"period_label": "2024-2025", "level": "terminale", "course": "Filière"}
    )
    assert not form.is_valid()
    assert "school_identifier" in form.errors


@pytest.mark.django_db
def test_form_rejects_bac_plus_level_without_higher_ed_school():
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(
        data={"period_label": "2024-2025", "level": "bac_1", "course": "Filière"}
    )
    assert not form.is_valid()
    assert "higher_ed_school_id" in form.errors


@pytest.mark.django_db
def test_form_rejects_unknown_school_identifier():
    from techpourtoutes.forms import BeneficiaryTrainingExperienceForm

    form = BeneficiaryTrainingExperienceForm(
        data={
            "period_label": "2024-2025",
            "level": "terminale",
            "course": "Filière",
            "school_identifier": "not-a-real-identifier",
        }
    )
    assert not form.is_valid()
    assert "school_identifier" in form.errors
