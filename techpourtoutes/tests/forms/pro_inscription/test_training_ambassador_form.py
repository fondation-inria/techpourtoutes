import pytest

from techpourtoutes.forms import ProTrainingAmbassadorForm

pytestmark = pytest.mark.django_db


def test_training_ambassador_form_saves_the_training_of_the_pro(
    pro, higher_ed_school, higher_ed_formation
):
    form = ProTrainingAmbassadorForm(
        data={"school_id": str(higher_ed_school.id), "formation_id": str(higher_ed_formation.pk)}
    )
    assert form.is_valid()

    experience = form.save(pro)

    assert experience.user == pro
    assert experience.school == higher_ed_school
    assert experience.formation == higher_ed_formation


def test_training_ambassador_form_requires_a_school_from_the_catalogue(higher_ed_formation):
    form = ProTrainingAmbassadorForm(data={"formation_id": str(higher_ed_formation.pk)})
    assert not form.is_valid()
    assert "school_id" in form.errors


def test_training_ambassador_form_refuses_a_school_outside_the_partner_list(higher_ed_formation):
    form = ProTrainingAmbassadorForm(
        data={
            "school_label": "École du bout du monde",
            "school_not_found": "on",
            "formation_id": str(higher_ed_formation.pk),
        }
    )
    assert not form.is_valid()
    assert "school_id" in form.errors
