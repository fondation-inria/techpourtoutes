import pytest


@pytest.mark.django_db
def test_form_prefills_from_experience(experience, higher_ed_school, higher_ed_formation):
    from techpourtoutes.forms import ProTrainingExperienceForm

    form = ProTrainingExperienceForm(experience=experience)
    assert form.initial["school_id"] == str(higher_ed_school.id)
    assert form.initial["school_label"] == higher_ed_school.display_label
    assert form.initial["formation_id"] == str(higher_ed_formation.pk)
    assert form.initial["formation_label"] == "Master Informatique"


@pytest.mark.django_db
def test_form_save_updates_experience(experience, higher_ed_school, higher_ed_formation):
    from techpourtoutes.forms import ProTrainingExperienceForm

    form = ProTrainingExperienceForm(
        data={
            "school_id": str(higher_ed_school.id),
            "level": "bac_5",
            "formation_id": str(higher_ed_formation.pk),
        }
    )
    assert form.is_valid(), form.errors
    form.save(experience)

    experience.refresh_from_db()
    assert experience.formation == higher_ed_formation
    assert experience.level == "bac_5"


@pytest.mark.django_db
def test_form_rejects_unknown_school(higher_ed_formation):
    from techpourtoutes.forms import ProTrainingExperienceForm

    form = ProTrainingExperienceForm(
        data={"school_id": "not-a-real-id", "formation_id": str(higher_ed_formation.pk)}
    )
    assert not form.is_valid()
    assert "school_id" in form.errors


@pytest.mark.django_db
def test_form_rejects_a_formation_the_school_does_not_teach(higher_ed_school, higher_ed_formation):
    from techpourtoutes.forms import ProTrainingExperienceForm
    from techpourtoutes.models import Formation

    elsewhere = Formation(onisep_id="9999", name="Diplôme d'ingénieur")
    elsewhere.save()

    form = ProTrainingExperienceForm(
        data={
            "school_id": str(higher_ed_school.id),
            "level": "bac_5",
            "formation_id": str(elsewhere.pk),
        }
    )

    assert not form.is_valid()
    assert "formation_id" in form.errors


@pytest.mark.django_db
def test_form_still_requires_a_school_without_the_fallback(higher_ed_formation):
    from techpourtoutes.forms import ProTrainingExperienceForm

    form = ProTrainingExperienceForm(
        data={"school_id": "", "level": "bac_5", "formation_id": str(higher_ed_formation.pk)}
    )

    assert not form.is_valid()
    assert "school_id" in form.errors


@pytest.mark.django_db
def test_a_missing_school_saves_the_experience_without_one(experience, higher_ed_formation):
    from techpourtoutes.forms import ProTrainingExperienceForm

    form = ProTrainingExperienceForm(
        data={
            "school_id": "",
            "school_label": "École du bout du monde",
            "school_not_found": "on",
            "level": "bac_5",
            "formation_id": str(higher_ed_formation.pk),
        }
    )
    assert form.is_valid(), form.errors
    form.save(experience)

    experience.refresh_from_db()
    assert experience.school is None
    assert experience.formation == higher_ed_formation
    assert form.has_missing_record


@pytest.mark.django_db
def test_a_missing_school_falls_back_to_the_higher_ed_catalogue(db):
    from techpourtoutes.forms import ProTrainingExperienceForm
    from techpourtoutes.models import Formation

    bac_pro = Formation(onisep_id="9999", name="Bac professionnel", secondary=True)
    bac_pro.save()

    form = ProTrainingExperienceForm(
        data={
            "school_id": "",
            "school_label": "École du bout du monde",
            "school_not_found": "on",
            "level": "bac_5",
            "formation_id": str(bac_pro.pk),
        }
    )

    assert not form.is_valid()
    assert "formation_id" in form.errors
