import pytest

from techpourtoutes.forms import ProEditUserForm


def _edit_user_data(**overrides):
    return {
        "first_name": "Alice",
        "last_name": "Martin",
        "phone": "0612345678",
        "structure_type": "company",
        "structure_name": "Inria",
        "job_title": "Chercheuse",
        "postal_code": "75001",
        **overrides,
    }


@pytest.mark.django_db
def test_edit_account_form_structure_name_required_when_she_works_in_a_structure():
    form = ProEditUserForm(data=_edit_user_data(structure_name=""))
    assert not form.is_valid()
    assert "structure_name" in form.errors


@pytest.mark.django_db
def test_edit_account_form_structure_name_not_required_when_jobless():
    form = ProEditUserForm(data=_edit_user_data(structure_type="jobless", structure_name=""))
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_edit_account_form_forgets_the_structure_name_of_a_retired_pro(pro):
    form = ProEditUserForm(data=_edit_user_data(structure_type="retired"))
    assert form.is_valid(), form.errors
    form.save(pro)

    pro.refresh_from_db()
    assert (pro.structure_type, pro.structure_name) == ("retired", "")


@pytest.mark.django_db
def test_edit_account_form_requires_a_structure_type():
    form = ProEditUserForm(data=_edit_user_data(structure_type=""))
    assert "structure_type" in form.errors


@pytest.mark.django_db
def test_edit_account_form_rejects_invalid_postal_code():
    form = ProEditUserForm(data=_edit_user_data(postal_code="123"))
    assert not form.is_valid()
    assert "postal_code" in form.errors


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("structure_type", "school_fixture"), [("school", "school"), ("higher_ed", "higher_ed_school")]
)
def test_edit_account_form_names_the_school_she_picked(request, structure_type, school_fixture):
    picked = request.getfixturevalue(school_fixture)
    form = ProEditUserForm(
        data=_edit_user_data(
            structure_type=structure_type,
            structure_name="Ce que la recherche affichait",
            structure_school_id=str(picked.pk),
        )
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["structure_name"] == picked.name


@pytest.mark.django_db
def test_edit_account_form_requires_a_school_picked_in_the_list(pro):
    form = ProEditUserForm(data=_edit_user_data(structure_type="school"), pro=pro)
    assert not form.is_valid()
    assert form.errors["structure_name"] == ["Sélectionnez un établissement dans la liste."]


def test_edit_account_form_takes_the_name_of_a_school_missing_from_the_list():
    form = ProEditUserForm(
        data=_edit_user_data(
            structure_type="higher_ed",
            structure_name="École de la Lune",
            structure_school_not_found="on",
        )
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["structure_name"] == "École de la Lune"


@pytest.mark.django_db
def test_edit_account_form_keeps_the_school_she_already_named(pro):
    pro.structure_type, pro.structure_name = "school", "Lycée de la Lune"
    form = ProEditUserForm(
        data=_edit_user_data(structure_type="school", structure_name="Lycée de la Lune"), pro=pro
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["structure_name"] == "Lycée de la Lune"


@pytest.mark.django_db
def test_edit_account_form_requires_a_school_picked_once_she_renames_hers(pro):
    pro.structure_type, pro.structure_name = "school", "Lycée de la Lune"
    form = ProEditUserForm(
        data=_edit_user_data(structure_type="school", structure_name="Lycée du Soleil"), pro=pro
    )
    assert not form.is_valid()
    assert form.errors["structure_name"] == ["Sélectionnez un établissement dans la liste."]
