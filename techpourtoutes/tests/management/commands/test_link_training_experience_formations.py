import pytest
from django.core.management import call_command

from techpourtoutes.models import Formation, FormationAction, TrainingExperience

pytestmark = pytest.mark.django_db


def experience_for(beneficiary, school, course):
    experience = TrainingExperience(user=beneficiary, school=school, course=course)
    experience.save()
    return experience


def test_a_course_taught_by_the_school_wins_over_its_namesake(beneficiary, school, formation):
    elsewhere = Formation(onisep_id="9999", name="Spécialité mathématiques")
    elsewhere.save()
    experience = experience_for(beneficiary, school, "Spécialité mathématiques")

    call_command("link_training_experience_formations")

    experience.refresh_from_db()
    assert experience.formation == formation


def test_a_course_the_school_does_not_teach_is_matched_on_the_whole_referential(
    beneficiary, school, formation
):
    elsewhere = Formation(onisep_id="9999", name="Diplôme national du brevet")
    elsewhere.save()
    experience = experience_for(beneficiary, school, "diplôme national du brevet")

    call_command("link_training_experience_formations")

    experience.refresh_from_db()
    assert experience.formation == elsewhere


def test_an_unknown_course_leaves_the_formation_empty(beneficiary, school, formation):
    experience = experience_for(beneficiary, school, "Filière imaginaire")

    call_command("link_training_experience_formations")

    experience.refresh_from_db()
    assert experience.formation is None


def test_an_already_linked_parcours_is_left_alone(beneficiary, school, formation):
    other = Formation(onisep_id="9999", name="Diplôme national du brevet")
    other.save()
    FormationAction(onisep_id="69397", formation=other, school=school).save()
    experience = TrainingExperience(
        user=beneficiary, school=school, formation=other, course="Spécialité mathématiques"
    )
    experience.save()

    call_command("link_training_experience_formations")

    experience.refresh_from_db()
    assert experience.formation == other


def test_a_parcours_without_a_school_is_matched_on_the_whole_referential(beneficiary, formation):
    experience = experience_for(beneficiary, None, "Spécialité mathématiques")

    call_command("link_training_experience_formations")

    experience.refresh_from_db()
    assert experience.formation == formation
