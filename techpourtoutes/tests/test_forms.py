import pytest


@pytest.mark.django_db
def test_pro_form_valid(valid_pro_data):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(data=valid_pro_data)
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_pro_form_missing_required_field(valid_pro_data):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(data={**valid_pro_data, "phone": ""})
    assert not form.is_valid()
    assert "phone" in form.errors


@pytest.mark.django_db
def test_pro_form_duplicate_email(valid_pro_data):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(data=valid_pro_data)
    assert form.is_valid()
    form.save()

    form2 = EngagementForm(data=valid_pro_data)
    assert not form2.is_valid()
    assert "email" in form2.errors


@pytest.mark.django_db
def test_pro_form_save_creates_pro(valid_pro_data):
    from techpourtoutes.forms import EngagementForm
    from techpourtoutes.models import Pro

    form = EngagementForm(data=valid_pro_data)
    assert form.is_valid()
    pro = form.save()
    assert isinstance(pro, Pro)
    assert Pro.objects.filter(email=valid_pro_data["email"]).exists()


@pytest.mark.django_db
def test_pro_form_invalid_professional_situation(valid_pro_data):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(data={**valid_pro_data, "professional_situation": "not-a-choice"})
    assert not form.is_valid()
    assert "professional_situation" in form.errors


@pytest.mark.django_db
def test_pro_form_blank_professional_situation(valid_pro_data):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(data={**valid_pro_data, "professional_situation": ""})
    assert not form.is_valid()
    assert "professional_situation" in form.errors


@pytest.mark.django_db
def test_pro_form_requires_terms_accepted(valid_pro_data):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(data={**valid_pro_data, "terms_accepted": False})
    assert not form.is_valid()
    assert "terms_accepted" in form.errors


@pytest.mark.django_db
def test_pro_form_invalid_civility(valid_pro_data):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(data={**valid_pro_data, "civility": "Mademoiselle"})
    assert not form.is_valid()
    assert "civility" in form.errors


@pytest.mark.django_db
def test_pro_form_structure_name_required_when_working(valid_pro_data):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(data={**valid_pro_data, "structure_name": ""})
    assert not form.is_valid()
    assert "structure_name" in form.errors


@pytest.mark.django_db
def test_pro_form_rejects_invalid_postal_code(valid_pro_data):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(data={**valid_pro_data, "postal_code": "123"})
    assert not form.is_valid()
    assert "postal_code" in form.errors


@pytest.mark.django_db
def test_pro_form_structure_name_not_required_when_retired(valid_pro_data):
    from techpourtoutes.forms import EngagementForm

    data = {
        **valid_pro_data,
        "professional_situation": "retired",
        "structure_name": "",
    }
    form = EngagementForm(data=data)
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_pro_form_with_pro_email_is_disabled(pro):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(pro=pro)
    assert form.fields["email"].disabled


@pytest.mark.django_db
def test_pro_form_with_pro_sets_initial_values(pro):
    from techpourtoutes.forms import EngagementForm

    form = EngagementForm(pro=pro)
    assert form.initial["email"] == pro.email
    assert form.initial["first_name"] == pro.first_name
    assert form.initial["last_name"] == pro.last_name


@pytest.mark.django_db
def test_pro_form_with_pro_terms_not_required(pro):
    from techpourtoutes.forms import EngagementForm

    data = {
        "civility": pro.civility,
        "first_name": pro.first_name,
        "last_name": pro.last_name,
        "email": pro.email,
        "phone": str(pro.phone),
        "postal_code": pro.postal_code,
        "professional_situation": pro.professional_situation,
        "job_title": pro.job_title,
        "structure_name": pro.structure_name,
    }
    form = EngagementForm(data=data, pro=pro)
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_pro_form_with_pro_allows_own_email(pro):
    from techpourtoutes.forms import EngagementForm

    data = {
        "civility": pro.civility,
        "first_name": pro.first_name,
        "last_name": pro.last_name,
        "email": pro.email,
        "phone": str(pro.phone),
        "postal_code": pro.postal_code,
        "professional_situation": pro.professional_situation,
        "job_title": pro.job_title,
        "structure_name": pro.structure_name,
        "terms_accepted": True,
    }
    form = EngagementForm(data=data, pro=pro)
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_pro_form_with_pro_save_updates_in_place(pro):
    from techpourtoutes.forms import EngagementForm
    from techpourtoutes.models import Pro

    data = {
        "civility": pro.civility,
        "first_name": "Nouveau Prénom",
        "last_name": pro.last_name,
        "email": pro.email,
        "phone": str(pro.phone),
        "postal_code": "69001",
        "professional_situation": pro.professional_situation,
        "job_title": "Nouveau métier",
        "structure_name": pro.structure_name,
        "terms_accepted": True,
    }
    form = EngagementForm(data=data, pro=pro)
    assert form.is_valid(), form.errors
    saved = form.save()

    assert saved.pk == pro.pk
    assert Pro.objects.count() == 1
    pro.refresh_from_db()
    assert pro.first_name == "Nouveau Prénom"
    assert pro.postal_code == "69001"


def _account_edit_data(**overrides):
    return {
        "first_name": "Alice",
        "last_name": "Martin",
        "phone": "0612345678",
        "professional_situation": "working",
        "structure_name": "Inria",
        "job_title": "Chercheuse",
        "postal_code": "75001",
        **overrides,
    }


@pytest.mark.django_db
def test_account_edit_form_structure_name_required_when_working():
    from techpourtoutes.forms import AccountEditForm

    form = AccountEditForm(data=_account_edit_data(structure_name=""))
    assert not form.is_valid()
    assert "structure_name" in form.errors


@pytest.mark.django_db
def test_account_edit_form_structure_name_not_required_when_jobless():
    from techpourtoutes.forms import AccountEditForm

    form = AccountEditForm(
        data=_account_edit_data(professional_situation="jobless", structure_name="")
    )
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_account_edit_form_rejects_invalid_postal_code():
    from techpourtoutes.forms import AccountEditForm

    form = AccountEditForm(data=_account_edit_data(postal_code="123"))
    assert not form.is_valid()
    assert "postal_code" in form.errors
