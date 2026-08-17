import pytest
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_training_experience_links_pro_and_school(pro, higher_ed_school):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(
        user=pro, school=higher_ed_school, out_of_scope_formation_name="Master Informatique"
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
        out_of_scope_formation_name="Spécialité mathématiques",
    )
    experience.save()

    assert experience in beneficiary.training_experiences.all()
    assert experience in school.training_experiences.all()


@pytest.mark.django_db
def test_training_experience_labels_come_from_the_linked_records(beneficiary, school, formation):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(user=beneficiary, school=school, formation=formation)

    assert experience.school_label == school.display_label
    assert experience.formation_label == formation.name


def test_training_experience_labels_fall_back_to_the_out_of_scope_names():
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(
        out_of_scope_school_name="Lycée hors catalogue",
        out_of_scope_formation_name="Bac pro maréchalerie",
    )

    assert experience.school_label == "Lycée hors catalogue"
    assert experience.formation_label == "Bac pro maréchalerie"


@pytest.mark.django_db
def test_training_experience_str_names_the_beneficiary_and_both_labels(
    beneficiary, school, formation
):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(user=beneficiary, school=school, formation=formation)

    assert str(experience) == (
        f"{beneficiary.full_name} – {school.display_label} - {formation.name}"
    )


@pytest.mark.django_db
def test_training_experience_needs_a_school_or_its_name(beneficiary, formation):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(user=beneficiary, formation=formation)

    with pytest.raises(ValidationError):
        experience.save()


@pytest.mark.django_db
def test_training_experience_refuses_a_school_and_its_name_at_once(beneficiary, school, formation):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(
        user=beneficiary,
        school=school,
        formation=formation,
        out_of_scope_school_name="Lycée hors catalogue",
    )

    with pytest.raises(ValidationError):
        experience.save()


@pytest.mark.django_db
def test_training_experience_needs_a_formation_or_its_name(beneficiary, school):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(user=beneficiary, school=school)

    with pytest.raises(ValidationError):
        experience.save()


@pytest.mark.django_db
def test_training_experience_refuses_a_formation_and_its_name_at_once(
    beneficiary, school, formation
):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(
        user=beneficiary,
        school=school,
        formation=formation,
        out_of_scope_formation_name="Bac pro maréchalerie",
    )

    with pytest.raises(ValidationError):
        experience.save()


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
        out_of_scope_formation_name="Terminale",
    )
    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.SECONDE,
        start_date=date(2022, 9, 1),
        end_date=date(2023, 8, 31),
        out_of_scope_formation_name="Seconde",
    )
    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.PREMIERE,
        start_date=date(2023, 9, 1),
        end_date=date(2024, 8, 31),
        out_of_scope_formation_name="Première",
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
        out_of_scope_formation_name="Terminale",
    )
    duplicate = TrainingExperience(
        user=beneficiary,
        school=school,
        level=Level.PREMIERE,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 8, 31),
        out_of_scope_formation_name="Première",
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
