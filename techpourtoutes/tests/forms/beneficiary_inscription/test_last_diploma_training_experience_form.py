import pytest

from techpourtoutes.forms import BeneficiaryLastDiplomaTrainingExperienceForm
from techpourtoutes.models import Level, TrainingExperience
from techpourtoutes.utils.school_year import (
    current_school_year_label,
    current_school_year_start_date,
    school_year_dates,
)

# Three school years back, so the label stays inside the offered window whatever the year is.
_DIPLOMA_YEAR = current_school_year_start_date().year - 3
PERIOD_LABEL = f"{_DIPLOMA_YEAR}-{_DIPLOMA_YEAR + 1}"


def _valid_data(formation, **overrides):
    return {
        "period_label": PERIOD_LABEL,
        "level": Level.TERMINALE,
        "formation_label": formation.name,
        "formation_id": str(formation.pk),
        **overrides,
    }


def _with_school(school, formation, **overrides):
    data = _valid_data(
        formation,
        school_label=school.location_label,
        school_id=str(school.pk),
    )
    return data | overrides


def _with_higher_ed_school(higher_ed_school, higher_ed_formation, **overrides):
    data = _valid_data(
        higher_ed_formation,
        level=Level.BAC_3,
        school_id=str(higher_ed_school.pk),
        school_label=higher_ed_school.display_label,
    )
    return data | overrides


@pytest.mark.django_db
def test_save_creates_a_training_experience_for_the_chosen_school_year(
    beneficiary, school, formation
):
    form = BeneficiaryLastDiplomaTrainingExperienceForm(data=_with_school(school, formation))
    assert form.is_valid(), form.errors

    experience = form.save(beneficiary)

    assert experience.user == beneficiary
    assert experience.school == school
    assert experience.level == Level.TERMINALE
    assert experience.formation == formation
    assert (experience.start_date, experience.end_date) == school_year_dates(PERIOD_LABEL)
    assert experience.start_date.year == _DIPLOMA_YEAR


@pytest.mark.django_db
def test_save_creates_a_training_experience_with_a_higher_ed_school(
    beneficiary, higher_ed_school, higher_ed_formation
):
    form = BeneficiaryLastDiplomaTrainingExperienceForm(
        data=_with_higher_ed_school(higher_ed_school, higher_ed_formation)
    )
    assert form.is_valid(), form.errors

    experience = form.save(beneficiary)

    assert experience.school == higher_ed_school
    assert experience.level == Level.BAC_3


def test_form_offers_every_level_a_beneficiary_can_declare():
    """Not the whole `Level` enum: its finer members only describe the imported formations."""
    form = BeneficiaryLastDiplomaTrainingExperienceForm()
    offered = dict(form.fields["level"].choices)

    assert set(TrainingExperience.LEVELS) <= set(offered)


def test_form_stops_at_the_current_school_year():
    # A diploma can't be obtained in a school year that hasn't started yet.
    form = BeneficiaryLastDiplomaTrainingExperienceForm()
    offered = [label for label, _ in form.fields["period_label"].choices]

    assert offered[1] == current_school_year_label()
    assert len(offered) == 12


@pytest.mark.django_db
def test_form_rejects_an_unknown_school(school, formation):
    form = BeneficiaryLastDiplomaTrainingExperienceForm(
        data=_with_school(school, formation, school_id="9999999Z")
    )

    assert not form.is_valid()
    assert "school_id" in form.errors


@pytest.mark.django_db
def test_form_requires_an_establishment_matching_the_level(higher_ed_school, higher_ed_formation):
    # A secondary level with only a higher ed school selected leaves the school unresolved.
    form = BeneficiaryLastDiplomaTrainingExperienceForm(
        data=_with_higher_ed_school(higher_ed_school, higher_ed_formation, level=Level.TERMINALE)
    )

    assert not form.is_valid()
    assert "school_id" in form.errors


@pytest.mark.django_db
def test_form_rejects_an_unknown_school_year(school, formation):
    form = BeneficiaryLastDiplomaTrainingExperienceForm(
        data=_with_school(school, formation, period_label="1998-1999")
    )

    assert not form.is_valid()
    assert "period_label" in form.errors
