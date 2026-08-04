import pytest


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
