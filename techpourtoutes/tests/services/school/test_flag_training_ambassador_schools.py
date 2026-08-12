import pytest

from techpourtoutes.models import School
from techpourtoutes.services.school.flag_training_ambassador_schools import (
    FlagTrainingAmbassadorSchools,
)

pytestmark = pytest.mark.django_db

# Read off the committed files: the first three are in the curated list, the last one is in
# the higher-ed sample but deliberately absent from it.
LISTED = ("2735", "4170", "50")
UNLISTED = "13362"


@pytest.fixture
def schools(db):
    for onisep_id in (*LISTED, UNLISTED):
        School(onisep_id=onisep_id, name=f"Établissement {onisep_id}", higher_ed=True).save()


def test_only_the_listed_schools_are_flagged(schools):
    result = FlagTrainingAmbassadorSchools()

    assert result.success
    assert set(School.objects.training_ambassador().values_list("onisep_id", flat=True)) == set(
        LISTED
    )


def test_a_school_absent_from_the_list_loses_a_stale_flag(schools):
    School.objects.filter(onisep_id=UNLISTED).update(training_ambassador_eligible=True)

    FlagTrainingAmbassadorSchools()

    assert not School.objects.get(onisep_id=UNLISTED).training_ambassador_eligible


def test_listed_ids_without_a_school_are_inert(db):
    """Only 90 of the 609 curated ids have a row once the samples are imported."""
    School(onisep_id=LISTED[0], name="emlyon", higher_ed=True).save()

    result = FlagTrainingAmbassadorSchools()

    assert result.success
    assert School.objects.training_ambassador().count() == 1


def test_running_twice_changes_nothing(schools):
    FlagTrainingAmbassadorSchools()
    FlagTrainingAmbassadorSchools()

    assert School.objects.training_ambassador().count() == len(LISTED)
