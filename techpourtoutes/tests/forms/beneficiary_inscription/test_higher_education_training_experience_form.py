import pytest

from techpourtoutes.forms import BeneficiaryHigherEducationTrainingExperienceForm
from techpourtoutes.models import Level
from techpourtoutes.utils.school_year import (
    current_school_year_end_date,
    current_school_year_start_date,
)


def _valid_data(higher_ed_school, higher_ed_formation, **overrides):
    return {
        "level": Level.BAC_3,
        "formation_label": higher_ed_formation.name,
        "formation_id": str(higher_ed_formation.pk),
        "school_id": str(higher_ed_school.pk),
        "school_label": higher_ed_school.display_label,
        **overrides,
    }


@pytest.mark.django_db
def test_save_creates_a_training_experience_for_the_current_school_year(
    beneficiary, higher_ed_school, higher_ed_formation
):
    form = BeneficiaryHigherEducationTrainingExperienceForm(
        data=_valid_data(higher_ed_school, higher_ed_formation)
    )
    assert form.is_valid(), form.errors

    experience = form.save(beneficiary)

    assert experience.user == beneficiary
    assert experience.school == higher_ed_school
    assert experience.level == Level.BAC_3
    assert experience.formation == higher_ed_formation
    assert experience.start_date == current_school_year_start_date()
    assert experience.end_date == current_school_year_end_date()


@pytest.mark.django_db
def test_form_rejects_a_secondary_level(higher_ed_school, higher_ed_formation):
    form = BeneficiaryHigherEducationTrainingExperienceForm(
        data=_valid_data(higher_ed_school, higher_ed_formation, level=Level.TERMINALE)
    )

    assert not form.is_valid()
    assert "level" in form.errors


@pytest.mark.django_db
def test_form_rejects_an_unknown_higher_ed_school(higher_ed_school, higher_ed_formation):
    form = BeneficiaryHigherEducationTrainingExperienceForm(
        data=_valid_data(higher_ed_school, higher_ed_formation, school_id="not-a-uuid")
    )

    assert not form.is_valid()
    assert "school_id" in form.errors


@pytest.mark.django_db
def test_form_requires_a_higher_ed_school(higher_ed_school, higher_ed_formation):
    form = BeneficiaryHigherEducationTrainingExperienceForm(
        data=_valid_data(higher_ed_school, higher_ed_formation, school_id="")
    )

    assert not form.is_valid()
    assert "school_id" in form.errors


def test_form_ignores_a_level_answered_in_the_other_branch():
    # Going back and switching study status carries the previous level along with the answers.
    form = BeneficiaryHigherEducationTrainingExperienceForm(initial={"level": Level.TERMINALE})

    assert form["level"].value() == ""
