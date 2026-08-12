import pytest
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_training_experience_links_pro_and_school(pro, higher_ed_school):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(
        user=pro, school=higher_ed_school, course="Master Informatique"
    )
    experience.save()

    assert experience in pro.training_experiences.all()
    assert experience in higher_ed_school.training_experiences.all()


@pytest.mark.django_db
def test_training_experience_links_beneficiary_and_school(beneficiary, school):
    from datetime import date

    from techpourtoutes.models import Level, TrainingExperience

    experience = TrainingExperience(
        user=beneficiary,
        school=school,
        level=Level.TERMINALE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        course="Spécialité mathématiques",
    )
    experience.save()

    assert experience in beneficiary.training_experiences.all()
    assert experience in school.training_experiences.all()


@pytest.mark.django_db
def test_training_experiences_are_ordered_reverse_chronologically(beneficiary, school):
    from datetime import date

    from techpourtoutes.models import Level, TrainingExperience

    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.TERMINALE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        course="Terminale",
    )
    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.SECONDE,
        start_date=date(2022, 9, 1),
        end_date=date(2023, 8, 31),
        course="Seconde",
    )
    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.PREMIERE,
        start_date=date(2023, 9, 1),
        end_date=date(2024, 8, 31),
        course="Première",
    )

    labels = [experience.period_label for experience in beneficiary.training_experiences.all()]
    assert labels == ["2024-2025", "2023-2024", "2022-2023"]


@pytest.mark.django_db
def test_training_experience_rejects_duplicate_period_label_for_same_beneficiary(
    beneficiary, school
):
    from datetime import date

    from techpourtoutes.models import Level, TrainingExperience

    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.TERMINALE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        course="Terminale",
    )
    duplicate = TrainingExperience(
        user=beneficiary,
        school=school,
        level=Level.PREMIERE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        course="Première",
    )

    with pytest.raises(ValidationError):
        duplicate.save()


def test_training_experience_is_current_school_year():
    from datetime import date

    from techpourtoutes.models import TrainingExperience
    from techpourtoutes.utils.school_year import current_school_year_start_date

    current = TrainingExperience(start_date=current_school_year_start_date())
    past = TrainingExperience(start_date=date(2000, 9, 1))

    assert current.is_current_school_year
    assert not past.is_current_school_year


def test_training_experience_secondary_and_higher_ed_levels_partition_the_offered_levels():
    """Every level a beneficiary can declare must route to one périmètre of school search.

    The shared enum is wider than that — it also grades the imported formations — so the
    partition is over `LEVELS`, not over the whole `Level`.
    """
    from techpourtoutes.models import Level, TrainingExperience

    covered_levels = set(TrainingExperience.SECONDARY_LEVELS) | set(
        TrainingExperience.HIGHER_ED_LEVELS
    )

    assert covered_levels == set(TrainingExperience.LEVELS)
    assert set(TrainingExperience.SECONDARY_LEVELS).isdisjoint(TrainingExperience.HIGHER_ED_LEVELS)
    assert covered_levels <= set(Level)
