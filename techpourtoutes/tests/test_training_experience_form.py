import pytest


@pytest.fixture
def experience(pro, higher_ed_school):
    from techpourtoutes.models import TrainingExperience

    return TrainingExperience.objects.create(
        pro=pro, higher_ed_school=higher_ed_school, course="Master Informatique"
    )


@pytest.mark.django_db
def test_form_prefills_from_experience(experience, higher_ed_school):
    from techpourtoutes.forms import TrainingExperienceForm

    form = TrainingExperienceForm(experience=experience)
    assert form.initial["higher_ed_school_id"] == str(higher_ed_school.id)
    assert form.initial["higher_ed_school_label"] == higher_ed_school.display_label
    assert form.initial["course"] == "Master Informatique"


@pytest.mark.django_db
def test_form_save_updates_experience(experience, higher_ed_school):
    from techpourtoutes.forms import TrainingExperienceForm

    form = TrainingExperienceForm(
        data={"higher_ed_school_id": str(higher_ed_school.id), "course": "Doctorat"}
    )
    assert form.is_valid(), form.errors
    form.save(experience)

    experience.refresh_from_db()
    assert experience.course == "Doctorat"


@pytest.mark.django_db
def test_form_rejects_unknown_school():
    from techpourtoutes.forms import TrainingExperienceForm

    form = TrainingExperienceForm(data={"higher_ed_school_id": "not-a-real-id", "course": "X"})
    assert not form.is_valid()
    assert "higher_ed_school_id" in form.errors
