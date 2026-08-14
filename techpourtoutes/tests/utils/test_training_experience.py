from datetime import date

import pytest

from techpourtoutes.models import Level, TrainingExperience
from techpourtoutes.utils.school_year import (
    current_school_year_start_date,
    next_school_year_start_date,
)
from techpourtoutes.utils.training_experience import (
    training_experience_insertion_anchor,
    training_experience_slots,
)


@pytest.mark.django_db
def test_training_experience_slots_places_current_year_placeholder_after_future_experience(
    beneficiary, school
):
    next_year = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.BAC_1,
        start_date=next_school_year_start_date(),
        end_date=date(next_school_year_start_date().year + 1, 8, 31),
        out_of_scope_formation_name="Prépa",
    )

    slots = training_experience_slots(beneficiary.training_experiences.all())

    assert slots == [next_year, None]


@pytest.mark.django_db
def test_training_experience_slots_omits_placeholder_when_current_year_experience_exists(
    beneficiary, school
):
    current = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
        out_of_scope_formation_name="Terminale",
    )

    slots = training_experience_slots(beneficiary.training_experiences.all())

    assert slots == [current]


@pytest.mark.django_db
def test_training_experience_insertion_anchor_targets_current_year_slot_for_a_future_experience(
    beneficiary, school
):
    current = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.TERMINALE,
        start_date=current_school_year_start_date(),
        end_date=date(current_school_year_start_date().year + 1, 8, 31),
        out_of_scope_formation_name="Terminale",
    )

    anchor = training_experience_insertion_anchor(beneficiary, next_school_year_start_date())

    assert anchor == current.pk


@pytest.mark.django_db
def test_training_experience_insertion_anchor_targets_current_year_placeholder_when_missing(
    beneficiary,
):
    anchor = training_experience_insertion_anchor(beneficiary, next_school_year_start_date())

    assert anchor == "current-year"


@pytest.mark.django_db
def test_training_experience_insertion_anchor_returns_none_for_the_earliest_experience(
    beneficiary, school
):
    TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.SECONDE,
        start_date=date(2022, 9, 1),
        end_date=date(2023, 8, 31),
        out_of_scope_formation_name="Seconde",
    )

    anchor = training_experience_insertion_anchor(beneficiary, date(2018, 9, 1))

    assert anchor is None


@pytest.mark.django_db
def test_training_experience_insertion_anchor_excludes_the_experience_being_edited(
    beneficiary, school
):
    edited = TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.SECONDE,
        start_date=date(2022, 9, 1),
        end_date=date(2023, 8, 31),
        out_of_scope_formation_name="Seconde",
    )

    anchor = training_experience_insertion_anchor(
        beneficiary, date(2022, 9, 1), exclude_pk=edited.pk
    )

    assert anchor is None
