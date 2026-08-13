import pytest

from techpourtoutes.forms import BeneficiaryLastDiplomaTrainingExperienceForm
from techpourtoutes.models import TrainingExperience
from techpourtoutes.utils.school_year import (
    current_school_year_label,
    current_school_year_start_date,
    school_year_dates,
)

# Three school years back, so the label stays inside the offered window whatever the year is.
_DIPLOMA_YEAR = current_school_year_start_date().year - 3
PERIOD_LABEL = f"{_DIPLOMA_YEAR}-{_DIPLOMA_YEAR + 1}"


def _valid_data(**overrides):
    return {
        "period_label": PERIOD_LABEL,
        "level": TrainingExperience.Level.TERMINALE,
        "course": "Spécialité mathématiques",
        **overrides,
    }


def _with_school(school, **overrides):
    data = _valid_data(
        school_name=school.name,
        school_identifier=school.identifier,
        school_postal_code=school.postal_code,
    )
    return data | overrides


def _with_higher_ed_school(higher_ed_school, **overrides):
    data = _valid_data(
        level=TrainingExperience.Level.BAC_3,
        higher_ed_school_id=str(higher_ed_school.pk),
        higher_ed_school_label=higher_ed_school.display_label,
    )
    return data | overrides


@pytest.mark.django_db
def test_save_creates_a_training_experience_for_the_chosen_school_year(beneficiary, school):
    form = BeneficiaryLastDiplomaTrainingExperienceForm(data=_with_school(school))
    assert form.is_valid(), form.errors

    experience = form.save(beneficiary)

    assert experience.user == beneficiary
    assert experience.school == school
    assert experience.higher_ed_school is None
    assert experience.level == TrainingExperience.Level.TERMINALE
    assert experience.course == "Spécialité mathématiques"
    assert (experience.start_date, experience.end_date) == school_year_dates(PERIOD_LABEL)
    assert experience.start_date.year == _DIPLOMA_YEAR


@pytest.mark.django_db
def test_save_creates_a_training_experience_with_a_higher_ed_school(beneficiary, higher_ed_school):
    form = BeneficiaryLastDiplomaTrainingExperienceForm(
        data=_with_higher_ed_school(higher_ed_school)
    )
    assert form.is_valid(), form.errors

    experience = form.save(beneficiary)

    assert experience.higher_ed_school == higher_ed_school
    assert experience.school is None
    assert experience.level == TrainingExperience.Level.BAC_3


def test_form_offers_every_level():
    form = BeneficiaryLastDiplomaTrainingExperienceForm()
    offered = dict(form.fields["level"].choices)

    assert set(TrainingExperience.Level.values) <= set(offered)


def test_form_stops_at_the_current_school_year():
    # A diploma can't be obtained in a school year that hasn't started yet.
    form = BeneficiaryLastDiplomaTrainingExperienceForm()
    offered = [label for label, _ in form.fields["period_label"].choices]

    assert offered[1] == current_school_year_label()
    assert len(offered) == 12


@pytest.mark.django_db
def test_form_rejects_an_unknown_school(school):
    form = BeneficiaryLastDiplomaTrainingExperienceForm(
        data=_with_school(school, school_identifier="9999999Z")
    )

    assert not form.is_valid()
    assert "school_identifier" in form.errors


@pytest.mark.django_db
def test_form_requires_an_establishment_matching_the_level(higher_ed_school):
    # A secondary level with only a higher ed school selected leaves the school unresolved.
    form = BeneficiaryLastDiplomaTrainingExperienceForm(
        data=_with_higher_ed_school(higher_ed_school, level=TrainingExperience.Level.TERMINALE)
    )

    assert not form.is_valid()
    assert "school_identifier" in form.errors


@pytest.mark.django_db
def test_form_rejects_an_unknown_school_year(school):
    form = BeneficiaryLastDiplomaTrainingExperienceForm(
        data=_with_school(school, period_label="1998-1999")
    )

    assert not form.is_valid()
    assert "period_label" in form.errors
