import pytest


@pytest.mark.django_db
def test_form_prefills_from_experience(experience, higher_ed_school):
    from techpourtoutes.forms import ProTrainingExperienceForm

    form = ProTrainingExperienceForm(experience=experience)
    assert form.initial["higher_ed_school_id"] == str(higher_ed_school.id)
    assert form.initial["higher_ed_school_label"] == higher_ed_school.display_label
    assert form.initial["course"] == "Master Informatique"


@pytest.mark.django_db
def test_form_save_updates_experience(experience, higher_ed_school):
    from techpourtoutes.forms import ProTrainingExperienceForm

    form = ProTrainingExperienceForm(
        data={
            "higher_ed_school_id": str(higher_ed_school.id),
            "level": "bac_5",
            "course": "Doctorat",
        }
    )
    assert form.is_valid(), form.errors
    form.save(experience)

    experience.refresh_from_db()
    assert experience.course == "Doctorat"
    assert experience.level == "bac_5"


@pytest.mark.django_db
def test_form_rejects_unknown_school():
    from techpourtoutes.forms import ProTrainingExperienceForm

    form = ProTrainingExperienceForm(data={"higher_ed_school_id": "not-a-real-id", "course": "X"})
    assert not form.is_valid()
    assert "higher_ed_school_id" in form.errors
