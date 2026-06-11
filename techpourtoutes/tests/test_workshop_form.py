import pytest


def valid_data(**overrides):
    return {
        "civility": "Madame",
        "first_name": "Manon",
        "last_name": "Desbordes",
        "email": "manon@example.com",
        "job_title": "Enseignante",
        "structure_id": "0750001A",
        "structure_name": "Lycée Voltaire",
        "postal_code": "75011",
        "remark": "Une remarque",
        "ateliers": ["future_of_tech", "future_of_ia"],
        "terms_accepted": True,
        "manifeste_accepted": True,
        **overrides,
    }


@pytest.mark.django_db
def test_workshop_form_valid():
    from techpourtoutes.forms import WorkshopForm

    form = WorkshopForm(data=valid_data())
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_workshop_form_save_creates_pro_without_phone():
    from techpourtoutes.forms import WorkshopForm
    from techpourtoutes.models import Pro

    form = WorkshopForm(data=valid_data())
    assert form.is_valid(), form.errors
    pro = form.save()

    saved = Pro.objects.get(email="manon@example.com")
    assert saved.pk == pro.pk
    assert saved.phone == ""
    assert saved.professional_situation == "working"
    assert saved.structure_name == "Lycée Voltaire"
    assert saved.structure_id == "0750001A"
    assert saved.postal_code == "75011"
    assert saved.job_title == "Enseignante"


@pytest.mark.django_db
def test_workshop_form_requires_establishment():
    from techpourtoutes.forms import WorkshopForm

    form = WorkshopForm(data=valid_data(structure_id="", structure_name="", postal_code=""))
    assert not form.is_valid()
    assert "structure_name" in form.errors


@pytest.mark.django_db
def test_workshop_form_requires_ateliers():
    from techpourtoutes.forms import WorkshopForm

    form = WorkshopForm(data=valid_data(ateliers=[]))
    assert not form.is_valid()
    assert "ateliers" in form.errors


@pytest.mark.django_db
def test_workshop_form_requires_job_title():
    from techpourtoutes.forms import WorkshopForm

    form = WorkshopForm(data=valid_data(job_title=""))
    assert not form.is_valid()
    assert "job_title" in form.errors


@pytest.mark.django_db
def test_workshop_form_requires_terms_accepted():
    from techpourtoutes.forms import WorkshopForm

    form = WorkshopForm(data=valid_data(terms_accepted=False))
    assert not form.is_valid()
    assert "terms_accepted" in form.errors


@pytest.mark.django_db
def test_workshop_form_duplicate_email():
    from techpourtoutes.forms import WorkshopForm

    first = WorkshopForm(data=valid_data())
    assert first.is_valid()
    first.save()

    form = WorkshopForm(data=valid_data())
    assert not form.is_valid()
    assert "email" in form.errors


@pytest.mark.django_db
def test_workshop_form_exposes_remark_and_ateliers():
    from techpourtoutes.forms import WorkshopForm

    form = WorkshopForm(data=valid_data())
    assert form.is_valid(), form.errors
    assert form.cleaned_data["remark"] == "Une remarque"
    assert form.cleaned_data["ateliers"] == ["future_of_tech", "future_of_ia"]


@pytest.mark.django_db
def test_workshop_form_with_pro_email_is_disabled(pro):
    from techpourtoutes.forms import WorkshopForm

    form = WorkshopForm(pro=pro)
    assert form.fields["email"].disabled


@pytest.mark.django_db
def test_workshop_form_with_pro_sets_initial_values(pro):
    from techpourtoutes.forms import WorkshopForm

    form = WorkshopForm(pro=pro)
    assert form.initial["email"] == pro.email
    assert form.initial["first_name"] == pro.first_name


@pytest.mark.django_db
def test_workshop_form_with_pro_terms_not_required(pro):
    from techpourtoutes.forms import WorkshopForm

    data = valid_data(
        email=pro.email,
        # terms_accepted NOT submitted
    )
    del data["terms_accepted"]
    form = WorkshopForm(data=data, pro=pro)
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_workshop_form_with_pro_allows_own_email(pro):
    from techpourtoutes.forms import WorkshopForm

    data = valid_data(email=pro.email)
    form = WorkshopForm(data=data, pro=pro)
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_workshop_form_with_pro_save_updates_in_place(pro):
    from techpourtoutes.forms import WorkshopForm
    from techpourtoutes.models import Pro

    data = valid_data(
        email=pro.email,
        first_name="Modifiée",
        structure_name="Nouveau lycée",
        structure_id="0750002B",
        postal_code="69001",
    )
    form = WorkshopForm(data=data, pro=pro)
    assert form.is_valid(), form.errors
    saved = form.save()

    assert saved.pk == pro.pk
    assert Pro.objects.count() == 1
    pro.refresh_from_db()
    assert pro.first_name == "Modifiée"
    assert pro.structure_name == "Nouveau lycée"
