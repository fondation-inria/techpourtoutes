import pytest


def valid_data(**overrides):
    return {
        "civility": "Madame",
        "first_name": "Manon",
        "last_name": "Desbordes",
        "email": "manon@example.com",
        "phone": "0612345678",
        "structure_id": "0750001A",
        "structure_name": "Université Paris-Saclay",
        "postal_code": "75011",
        "terms_accepted": True,
        "manifeste_accepted": True,
        **overrides,
    }


@pytest.mark.django_db
def test_training_ambassador_form_valid():
    from techpourtoutes.forms import TrainingAmbassadorForm

    form = TrainingAmbassadorForm(data=valid_data())
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_training_ambassador_form_save_creates_student_pro():
    from techpourtoutes.forms import TrainingAmbassadorForm
    from techpourtoutes.models import Pro

    form = TrainingAmbassadorForm(data=valid_data())
    assert form.is_valid(), form.errors
    pro = form.save()

    saved = Pro.objects.get(email="manon@example.com")
    assert saved.pk == pro.pk
    assert saved.professional_situation == "student"
    assert saved.job_title == "Étudiante"
    assert saved.structure_name == "Université Paris-Saclay"
    assert saved.structure_id == "0750001A"
    assert saved.postal_code == "75011"


@pytest.mark.django_db
def test_training_ambassador_form_with_pro_save_updates_in_place(pro):
    from techpourtoutes.forms import TrainingAmbassadorForm
    from techpourtoutes.models import Pro

    data = valid_data(
        email=pro.email,
        first_name="Modifiée",
        structure_name="Nouvelle université",
        structure_id="0750002B",
        postal_code="69001",
    )
    form = TrainingAmbassadorForm(data=data, pro=pro)
    assert form.is_valid(), form.errors
    saved = form.save()

    assert saved.pk == pro.pk
    assert Pro.objects.count() == 1
    pro.refresh_from_db()
    assert pro.first_name == "Modifiée"
    assert pro.structure_name == "Nouvelle université"
    assert pro.professional_situation == "student"
    assert pro.job_title == "Étudiante"


@pytest.mark.django_db
def test_training_ambassador_form_does_not_prefill_structure_name(pro):
    from techpourtoutes.forms import TrainingAmbassadorForm

    form = TrainingAmbassadorForm(pro=pro)
    assert not form.initial.get("structure_name")
