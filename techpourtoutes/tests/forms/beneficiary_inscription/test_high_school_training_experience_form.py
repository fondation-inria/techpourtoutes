import pytest

from techpourtoutes.forms import BeneficiaryHighSchoolTrainingExperienceForm
from techpourtoutes.models import Level
from techpourtoutes.utils.school_year import (
    current_school_year_end_date,
    current_school_year_start_date,
)


def _valid_data(school, formation, **overrides):
    return {
        "level": Level.TERMINALE,
        "formation_label": formation.name,
        "formation_id": str(formation.pk),
        "school_label": school.location_label,
        "school_id": str(school.pk),
        **overrides,
    }


@pytest.mark.django_db
def test_save_creates_a_training_experience_for_the_current_school_year(
    beneficiary, school, formation
):
    form = BeneficiaryHighSchoolTrainingExperienceForm(data=_valid_data(school, formation))
    assert form.is_valid(), form.errors

    experience = form.save(beneficiary)

    assert experience.user == beneficiary
    assert experience.school == school
    assert experience.level == Level.TERMINALE
    assert experience.formation == formation
    assert experience.start_date == current_school_year_start_date()
    assert experience.end_date == current_school_year_end_date()


@pytest.mark.django_db
def test_form_rejects_a_higher_education_level(school, formation):
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(school, formation, level=Level.BAC_3)
    )

    assert not form.is_valid()
    assert "level" in form.errors


@pytest.mark.django_db
def test_form_rejects_an_unknown_school(school, formation):
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(school, formation, school_id="9999999Z")
    )

    assert not form.is_valid()
    assert "school_id" in form.errors


@pytest.mark.django_db
def test_form_requires_a_school(school, formation):
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(school, formation, school_id="")
    )

    assert not form.is_valid()
    assert "school_id" in form.errors


def test_form_ignores_a_level_answered_in_the_other_branch():
    # Going back and switching study status carries the previous level along with the answers.
    form = BeneficiaryHighSchoolTrainingExperienceForm(initial={"level": Level.BAC_3})

    assert form["level"].value() == ""


@pytest.mark.django_db
def test_form_requires_a_formation_once_the_school_is_known(school, formation):
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(school, formation, formation_id="")
    )

    assert not form.is_valid()
    assert "formation_id" in form.errors


@pytest.mark.django_db
def test_form_rejects_a_formation_the_school_does_not_teach(school, formation):
    from techpourtoutes.models import Formation

    elsewhere = Formation(onisep_id="9999", name="Diplôme d'ingénieur")
    elsewhere.save()

    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(school, formation, formation_id=str(elsewhere.pk))
    )

    assert not form.is_valid()
    assert "formation_id" in form.errors


@pytest.mark.django_db
def test_form_reports_the_school_before_the_formation(school, formation):
    """No school, no perimeter: the formation cannot be resolved yet."""
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(school, formation, school_id="")
    )

    assert "school_id" in form.errors
    assert "formation_id" not in form.errors


@pytest.mark.django_db
def test_a_missing_school_still_resolves_a_formation_from_the_whole_catalogue(
    beneficiary, school, formation
):
    from techpourtoutes.models import Formation

    elsewhere = Formation(onisep_id="9999", name="Diplôme d'ingénieur", secondary=True)
    elsewhere.save()

    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(
            school,
            formation,
            school_id="",
            school_label="Lycée du bout du monde",
            school_not_found="on",
            formation_id=str(elsewhere.pk),
            formation_label=elsewhere.name,
        )
    )
    assert form.is_valid(), form.errors

    experience = form.save(beneficiary)

    assert experience.school is None
    assert experience.formation == elsewhere
    assert experience.level == Level.TERMINALE


@pytest.mark.django_db
def test_a_missing_school_never_resolves_a_higher_ed_only_formation(beneficiary, school):
    from techpourtoutes.models import Formation

    higher_ed_only = Formation(onisep_id="9999", name="Master Informatique", higher_ed=True)
    higher_ed_only.save()

    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(
            school,
            higher_ed_only,
            school_id="",
            school_label="Lycée du bout du monde",
            school_not_found="on",
            formation_id=str(higher_ed_only.pk),
            formation_label=higher_ed_only.name,
        )
    )

    assert not form.is_valid()
    assert "formation_id" in form.errors


@pytest.mark.django_db
def test_both_records_missing_saves_the_level_and_the_typed_names(beneficiary, school, formation):
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(
            school,
            formation,
            school_id="",
            school_label="Lycée du bout du monde",
            school_not_found="on",
            formation_id="",
            formation_label="Bac pro maréchalerie",
            formation_not_found="on",
        )
    )
    assert form.is_valid(), form.errors

    experience = form.save(beneficiary)

    assert experience.school is None
    assert experience.formation is None
    assert experience.level == Level.TERMINALE
    assert experience.out_of_scope_school_name == "Lycée du bout du monde"
    assert experience.out_of_scope_formation_name == "Bac pro maréchalerie"


@pytest.mark.django_db
def test_a_missing_school_requires_its_free_text_name(school, formation):
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(school, formation, school_id="", school_label="", school_not_found="on")
    )

    assert not form.is_valid()
    assert "school_label" in form.errors


@pytest.mark.django_db
def test_a_free_text_name_longer_than_its_column_is_a_form_error(school, formation):
    """The column would reject it on save, where the form can still say so under the field."""
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(
            school, formation, school_id="", school_label="L" * 351, school_not_found="on"
        )
    )

    assert not form.is_valid()
    assert "school_label" in form.errors


@pytest.mark.django_db
def test_a_missing_formation_requires_its_free_text_name(school, formation):
    form = BeneficiaryHighSchoolTrainingExperienceForm(
        data=_valid_data(
            school, formation, formation_id="", formation_label="", formation_not_found="on"
        )
    )

    assert not form.is_valid()
    assert "formation_label" in form.errors
