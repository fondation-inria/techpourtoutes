import pytest


@pytest.mark.django_db
def test_pro_form_valid(valid_pro_data):
    from techpourtoutes.forms import ProForm

    form = ProForm(data=valid_pro_data)
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_pro_form_missing_required_field(valid_pro_data):
    from techpourtoutes.forms import ProForm

    form = ProForm(data={**valid_pro_data, "phone": ""})
    assert not form.is_valid()
    assert "phone" in form.errors


@pytest.mark.django_db
def test_pro_form_duplicate_email(valid_pro_data):
    from techpourtoutes.forms import ProForm

    form = ProForm(data=valid_pro_data)
    assert form.is_valid()
    form.save()

    form2 = ProForm(data=valid_pro_data)
    assert not form2.is_valid()
    assert "email" in form2.errors


@pytest.mark.django_db
def test_pro_form_save_creates_pro(valid_pro_data):
    from techpourtoutes.forms import ProForm
    from techpourtoutes.models import Pro

    form = ProForm(data=valid_pro_data)
    assert form.is_valid()
    pro = form.save()
    assert isinstance(pro, Pro)
    assert Pro.objects.filter(email=valid_pro_data["email"]).exists()


@pytest.mark.django_db
def test_pro_form_invalid_professional_situation(valid_pro_data):
    from techpourtoutes.forms import ProForm

    form = ProForm(data={**valid_pro_data, "professional_situation": "not-a-choice"})
    assert not form.is_valid()
    assert "professional_situation" in form.errors


@pytest.mark.django_db
def test_pro_form_blank_professional_situation(valid_pro_data):
    from techpourtoutes.forms import ProForm

    form = ProForm(data={**valid_pro_data, "professional_situation": ""})
    assert not form.is_valid()
    assert "professional_situation" in form.errors


@pytest.mark.django_db
def test_pro_form_requires_terms_accepted(valid_pro_data):
    from techpourtoutes.forms import ProForm

    form = ProForm(data={**valid_pro_data, "terms_accepted": False})
    assert not form.is_valid()
    assert "terms_accepted" in form.errors


@pytest.mark.django_db
def test_pro_form_invalid_civility(valid_pro_data):
    from techpourtoutes.forms import ProForm

    form = ProForm(data={**valid_pro_data, "civility": "Mademoiselle"})
    assert not form.is_valid()
    assert "civility" in form.errors


@pytest.mark.django_db
def test_pro_form_structure_name_required_when_working(valid_pro_data):
    from techpourtoutes.forms import ProForm

    form = ProForm(data={**valid_pro_data, "structure_name": ""})
    assert not form.is_valid()
    assert "structure_name" in form.errors


@pytest.mark.django_db
def test_pro_form_structure_name_not_required_when_retired(valid_pro_data):
    from techpourtoutes.forms import ProForm

    data = {
        **valid_pro_data,
        "professional_situation": "retired",
        "structure_name": "",
    }
    form = ProForm(data=data)
    assert form.is_valid(), form.errors
