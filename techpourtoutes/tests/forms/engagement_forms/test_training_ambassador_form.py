import pytest


def valid_data(higher_ed_school_id, **overrides):
    return {
        "civility": "Madame",
        "first_name": "Manon",
        "last_name": "Desbordes",
        "email": "manon@example.com",
        "phone": "0612345678",
        "higher_ed_school_id": str(higher_ed_school_id),
        "course": "Master Informatique",
        "terms_accepted": True,
        "manifeste_accepted": True,
        **overrides,
    }


@pytest.mark.django_db
def test_training_ambassador_form_valid(higher_ed_school):
    from techpourtoutes.forms import TrainingAmbassadorForm

    form = TrainingAmbassadorForm(data=valid_data(higher_ed_school.id))
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_training_ambassador_form_save_creates_student_pro_and_experience(higher_ed_school):
    from techpourtoutes.forms import TrainingAmbassadorForm
    from techpourtoutes.models import Pro

    form = TrainingAmbassadorForm(data=valid_data(higher_ed_school.id))
    assert form.is_valid(), form.errors
    pro = form.save()
    form.after_save(pro)

    saved = Pro.objects.get(email="manon@example.com")
    assert saved.pk == pro.pk
    assert saved.professional_situation == "student"

    experience = saved.training_experiences.get()
    assert experience.higher_ed_school == higher_ed_school
    assert experience.course == "Master Informatique"


@pytest.mark.django_db
def test_training_ambassador_form_rejects_unknown_school(higher_ed_school):
    from techpourtoutes.forms import TrainingAmbassadorForm

    data = valid_data(higher_ed_school.id)
    data["higher_ed_school_id"] = "not-a-real-id"
    form = TrainingAmbassadorForm(data=data)
    assert not form.is_valid()
    assert "higher_ed_school_id" in form.errors


@pytest.mark.django_db
def test_training_ambassador_form_requires_course(higher_ed_school):
    from techpourtoutes.forms import TrainingAmbassadorForm

    form = TrainingAmbassadorForm(data=valid_data(higher_ed_school.id, course=""))
    assert not form.is_valid()
    assert "course" in form.errors


@pytest.mark.django_db
def test_training_ambassador_form_resubmitting_same_school_updates_experience(
    pro, higher_ed_school
):
    from techpourtoutes.forms import TrainingAmbassadorForm
    from techpourtoutes.models import TrainingExperience

    for course in ("Licence", "Master"):
        form = TrainingAmbassadorForm(
            data=valid_data(higher_ed_school.id, email=pro.email, course=course), pro=pro
        )
        assert form.is_valid(), form.errors
        saved = form.save()
        form.after_save(saved)

    experience = TrainingExperience.objects.get(pro=pro, higher_ed_school=higher_ed_school)
    assert experience.course == "Master"
