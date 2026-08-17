from datetime import date

import pytest
from django.core.management import call_command

from techpourtoutes.models import Level, School, TrainingExperience

pytestmark = pytest.mark.django_db


def legacy(name="Lycée Voltaire", uai="", siret="", suffix="0"):
    school = School(onisep_id=f"legacy-s-{suffix}", name=name, uai=uai, siret=siret)
    school.save()
    return school


def parcours(beneficiary, school, year=2023):
    return TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        level=Level.TERMINALE,
        start_date=date(year, 9, 1),
        end_date=date(year + 1, 8, 31),
        out_of_scope_formation_name="Spécialité mathématiques",
    )


def test_a_parcours_is_repointed_on_the_matching_uai(beneficiary):
    experience = parcours(beneficiary, legacy(uai="0750001A"))
    onisep = School(onisep_id="14008", uai="0750001A", name="Lycée Voltaire", secondary=True)
    onisep.save()

    call_command("remap_training_experience_schools")

    experience.refresh_from_db()
    assert experience.school == onisep
    assert School.objects.filter(onisep_id__startswith="legacy-").count() == 0


def test_a_shared_uai_is_resolved_deterministically(beneficiary):
    experience = parcours(beneficiary, legacy(uai="0750001A"))
    for onisep_id in ("14009", "14008"):
        School(onisep_id=onisep_id, uai="0750001A", name="Lycée Voltaire", secondary=True).save()

    call_command("remap_training_experience_schools")

    experience.refresh_from_db()
    assert experience.school.onisep_id == "14008"


def test_an_empty_uai_falls_back_on_the_siret(beneficiary):
    experience = parcours(beneficiary, legacy(siret="13002602400054"))
    onisep = School(
        onisep_id="490", siret="13002602400054", name="Université Paris-Saclay", higher_ed=True
    )
    onisep.save()

    call_command("remap_training_experience_schools")

    experience.refresh_from_db()
    assert experience.school == onisep


def test_an_unmatched_parcours_keeps_the_school_name_it_displayed(beneficiary):
    """A placeholder we cannot resolve leaves its name on the parcours, then goes away."""
    placeholder = legacy(uai="0000000X")
    experience = parcours(beneficiary, placeholder)
    School(onisep_id="14008", uai="0750001A", name="Lycée Voltaire", secondary=True).save()

    call_command("remap_training_experience_schools")

    experience.refresh_from_db()
    assert experience.school is None
    assert experience.out_of_scope_school_name == "Lycée Voltaire"
    assert TrainingExperience.objects.count() == 1
    assert School.objects.legacy().count() == 0


def test_a_blank_uai_never_matches_a_school_without_one(beneficiary):
    experience = parcours(beneficiary, legacy())
    School(onisep_id="14008", uai="", siret="", name="Sans identifiant", secondary=True).save()

    call_command("remap_training_experience_schools")

    experience.refresh_from_db()
    assert experience.school is None


def test_running_twice_is_a_no_op(beneficiary):
    experience = parcours(beneficiary, legacy(uai="0750001A"))
    School(onisep_id="14008", uai="0750001A", name="Lycée Voltaire", secondary=True).save()
    call_command("remap_training_experience_schools")

    call_command("remap_training_experience_schools")

    experience.refresh_from_db()
    assert experience.school.onisep_id == "14008"
