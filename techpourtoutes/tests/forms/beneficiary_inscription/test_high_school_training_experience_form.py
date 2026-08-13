import pytest

from techpourtoutes.forms import BeneficiaryHighSchoolTrainingExperienceForm
from techpourtoutes.models import TrainingExperience
from techpourtoutes.utils.school_year import (
    current_school_year_end_date,
    current_school_year_start_date,
)


def _valid_data(school, **overrides):
    return {
        "level": TrainingExperience.Level.TERMINALE,
        "course": "Spécialité mathématiques",
        "school_name": school.name,
        "school_identifier": school.identifier,
        "school_postal_code": school.postal_code,
        **overrides,
    }


@pytest.mark.django_db
def test_save_creates_a_training_experience_for_the_current_school_year(beneficiary, school):
    form = BeneficiaryHighSchoolTrainingExperienceForm(data=_valid_data(school))
    assert form.is_valid(), form.errors

    experience = form.save(beneficiary)

    assert experience.user == beneficiary
    assert experience.school == school
    assert experience.higher_ed_school is None
    assert experience.level == TrainingExperience.Level.TERMINALE
    assert experience.course == "Spécialité mathématiques"
    assert experience.start_date == current_school_year_start_date()
    assert experience.end_date == current_school_year_end_date()


@pytest.mark.django_db
def test_form_rejects_a_higher_education_level(school):
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(school, level=TrainingExperience.Level.BAC_3)
    )

    assert not form.is_valid()
    assert "level" in form.errors


@pytest.mark.django_db
def test_form_rejects_an_unknown_school(school):
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(school, school_identifier="9999999Z")
    )

    assert not form.is_valid()
    assert "school_identifier" in form.errors


@pytest.mark.django_db
def test_form_requires_a_school(school):
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(school, school_identifier="")
    )

    assert not form.is_valid()
    assert "school_identifier" in form.errors


def test_form_ignores_a_level_answered_in_the_other_branch():
    # Going back and switching study status carries the previous level along with the answers.
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        initial={"level": TrainingExperience.Level.BAC_3}
    )

    assert form["level"].value() == ""
