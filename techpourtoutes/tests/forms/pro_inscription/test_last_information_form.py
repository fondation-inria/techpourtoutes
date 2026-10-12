import pytest

from techpourtoutes.forms import ProLastInformationForm


def _last_information(**overrides):
    return {
        "structure_type": "company",
        "structure_name": "Inria",
        "job_title": "Chercheuse",
        "phone": "0612345678",
        "postal_code": "75011",
        **overrides,
    }


def test_last_information_form_accepts_complete_information():
    assert ProLastInformationForm(data=_last_information()).is_valid()


def test_last_information_form_requires_a_structure_name_for_a_structure():
    form = ProLastInformationForm(data=_last_information(structure_name=""))
    assert not form.is_valid()
    assert "structure_name" in form.errors


@pytest.mark.parametrize("structure_type", ["retired", "jobless"])
def test_last_information_form_needs_no_structure_name_without_a_structure(structure_type):
    form = ProLastInformationForm(
        data=_last_information(structure_type=structure_type, structure_name="")
    )
    assert form.is_valid()


def test_last_information_form_requires_every_other_field():
    form = ProLastInformationForm(data={})
    assert not form.is_valid()
    assert {"structure_type", "job_title", "phone", "postal_code"} <= set(form.errors)


def test_last_information_form_rejects_an_invalid_postal_code():
    form = ProLastInformationForm(data=_last_information(postal_code="7501"))
    assert not form.is_valid()
    assert "postal_code" in form.errors


def test_last_information_form_keeps_the_job_given_for_the_workshop():
    form = ProLastInformationForm(
        data=_last_information(job_title="Chercheuse"), workshop_job_title="Enseignante"
    )
    assert form.fields["job_title"].disabled
    assert form.is_valid()
    assert form.cleaned_data["job_title"] == "Enseignante"
