import pytest


def valid_data(higher_ed_school_id, formation_pk, **overrides):
    return {
        "civility": "Madame",
        "first_name": "Manon",
        "last_name": "Desbordes",
        "email": "manon@example.com",
        "phone": "0612345678",
        "school_id": str(higher_ed_school_id),
        "formation_id": str(formation_pk),
        "terms_accepted": True,
        "manifeste_accepted": True,
        **overrides,
    }


@pytest.mark.django_db
def test_training_ambassador_form_valid(higher_ed_school, higher_ed_formation):
    from techpourtoutes.forms import TrainingAmbassadorForm

    form = TrainingAmbassadorForm(data=valid_data(higher_ed_school.id, higher_ed_formation.pk))
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_training_ambassador_form_save_creates_student_pro_and_experience(
    higher_ed_school, higher_ed_formation
):
    from techpourtoutes.forms import TrainingAmbassadorForm
    from techpourtoutes.models import Pro
    from techpourtoutes.utils.school_year import (
        current_school_year_end_date,
        current_school_year_start_date,
    )

    form = TrainingAmbassadorForm(data=valid_data(higher_ed_school.id, higher_ed_formation.pk))
    assert form.is_valid(), form.errors
    pro = form.save()
    form.after_save(pro)

    saved = Pro.objects.get(email="manon@example.com")
    assert saved.pk == pro.pk
    assert saved.professional_situation == "student"

    experience = saved.training_experiences.get()
    assert experience.school == higher_ed_school
    assert experience.formation == higher_ed_formation
    assert experience.start_date == current_school_year_start_date()
    assert experience.end_date == current_school_year_end_date()


@pytest.mark.django_db
def test_training_ambassador_form_rejects_unknown_school(higher_ed_school, higher_ed_formation):
    from techpourtoutes.forms import TrainingAmbassadorForm

    data = valid_data(higher_ed_school.id, higher_ed_formation.pk)
    data["school_id"] = "not-a-real-id"
    form = TrainingAmbassadorForm(data=data)
    assert not form.is_valid()
    assert "school_id" in form.errors


@pytest.mark.django_db
def test_training_ambassador_form_requires_a_formation(higher_ed_school, higher_ed_formation):
    from techpourtoutes.forms import TrainingAmbassadorForm

    form = TrainingAmbassadorForm(
        data=valid_data(higher_ed_school.id, higher_ed_formation.pk, formation_id="")
    )
    assert not form.is_valid()
    assert "formation_id" in form.errors


@pytest.mark.django_db
def test_training_ambassador_form_rejects_a_formation_the_school_does_not_teach(
    higher_ed_school, higher_ed_formation
):
    from techpourtoutes.forms import TrainingAmbassadorForm
    from techpourtoutes.models import Formation

    elsewhere = Formation(onisep_id="9999", name="Diplôme d'ingénieur")
    elsewhere.save()

    form = TrainingAmbassadorForm(
        data=valid_data(
            higher_ed_school.id, higher_ed_formation.pk, formation_id=str(elsewhere.pk)
        )
    )
    assert not form.is_valid()
    assert "formation_id" in form.errors


@pytest.mark.django_db
def test_training_ambassador_form_resubmitting_same_school_updates_experience(
    pro, higher_ed_school, higher_ed_formation
):
    from techpourtoutes.forms import TrainingAmbassadorForm
    from techpourtoutes.models import Formation, FormationAction, TrainingExperience

    licence = Formation(onisep_id="9999", name="Licence informatique", higher_ed=True)
    licence.save()
    FormationAction(onisep_id="69397", formation=licence, school=higher_ed_school).save()

    for formation in (licence, higher_ed_formation):
        form = TrainingAmbassadorForm(
            data=valid_data(higher_ed_school.id, formation.pk, email=pro.email), pro=pro
        )
        assert form.is_valid(), form.errors
        saved = form.save()
        form.after_save(saved)

    experience = TrainingExperience.objects.get(user=pro, school=higher_ed_school)
    assert experience.formation == higher_ed_formation


@pytest.mark.django_db
def test_training_ambassador_form_still_requires_a_school_without_the_fallback(
    higher_ed_school, higher_ed_formation
):
    from techpourtoutes.forms import TrainingAmbassadorForm

    form = TrainingAmbassadorForm(
        data=valid_data(higher_ed_school.id, higher_ed_formation.pk, school_id="")
    )

    assert not form.is_valid()
    assert "school_id" in form.errors


@pytest.mark.django_db
def test_a_missing_school_creates_the_experience_without_one(
    higher_ed_school, higher_ed_formation
):
    from techpourtoutes.forms import TrainingAmbassadorForm

    form = TrainingAmbassadorForm(
        data=valid_data(
            higher_ed_school.id,
            higher_ed_formation.pk,
            school_id="",
            school_label="École du bout du monde",
            school_not_found="on",
        )
    )
    assert form.is_valid(), form.errors
    assert form.has_missing_record

    experience = form.after_save(form.save())

    assert experience.school is None
    assert experience.formation == higher_ed_formation


@pytest.mark.django_db
def test_a_missing_school_falls_back_to_the_higher_ed_catalogue(higher_ed_school):
    from techpourtoutes.forms import TrainingAmbassadorForm
    from techpourtoutes.models import Formation

    bac_pro = Formation(onisep_id="9999", name="Bac professionnel", secondary=True)
    bac_pro.save()

    form = TrainingAmbassadorForm(
        data=valid_data(
            higher_ed_school.id,
            bac_pro.pk,
            school_id="",
            school_label="École du bout du monde",
            school_not_found="on",
        )
    )

    assert not form.is_valid()
    assert "formation_id" in form.errors
