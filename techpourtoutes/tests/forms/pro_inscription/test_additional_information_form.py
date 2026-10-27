import pytest

from techpourtoutes.forms import ProAdditionalInformationForm
from techpourtoutes.models import Pro


def _additional_information(**overrides):
    return {
        "structure_type": "company",
        "structure_name": "Inria",
        "job_title": "Chercheuse",
        "phone": "0612345678",
        "postal_code": "75011",
        **overrides,
    }


def test_additional_information_form_accepts_complete_information():
    assert ProAdditionalInformationForm(data=_additional_information()).is_valid()


def test_additional_information_form_requires_a_structure_name_for_a_structure():
    form = ProAdditionalInformationForm(data=_additional_information(structure_name=""))
    assert not form.is_valid()
    assert "structure_name" in form.errors


@pytest.mark.parametrize("structure_type", ["retired", "jobless"])
def test_additional_information_form_needs_no_structure_name_without_a_structure(structure_type):
    form = ProAdditionalInformationForm(
        data=_additional_information(structure_type=structure_type, structure_name="")
    )
    assert form.is_valid()


def test_additional_information_form_requires_every_other_field():
    form = ProAdditionalInformationForm(data={})
    assert not form.is_valid()
    assert {"structure_type", "job_title", "phone", "postal_code"} <= set(form.errors)


def test_additional_information_form_rejects_an_invalid_postal_code():
    form = ProAdditionalInformationForm(data=_additional_information(postal_code="7501"))
    assert not form.is_valid()
    assert "postal_code" in form.errors


def _workshop(**overrides):
    return {
        "school_label": "Lycée Voltaire",
        "job_title": "Enseignante",
        "postal_code": "75005",
        **overrides,
    }


def test_additional_information_form_keeps_the_school_and_job_given_for_the_workshop():
    form = ProAdditionalInformationForm(data=_additional_information(), workshop=_workshop())
    assert set(form.fields) == {"phone", "postal_code"}
    assert form.is_valid()
    assert form.cleaned_data["structure_type"] == "school"
    assert form.cleaned_data["structure_name"] == "Lycée Voltaire"
    assert form.cleaned_data["job_title"] == "Enseignante"


def test_additional_information_form_asks_the_job_of_another_mission_at_the_school():
    form = ProAdditionalInformationForm(
        data=_additional_information(job_title="Infirmière"),
        workshop=_workshop(job_title="Autre mission au sein d'un établissement"),
    )
    assert set(form.fields) == {"job_title", "phone", "postal_code"}
    assert form.is_valid()
    assert form.cleaned_data["structure_name"] == "Lycée Voltaire"
    assert form.cleaned_data["job_title"] == "Infirmière"


@pytest.mark.parametrize(
    "job_title",
    ["DRANE / DAN / IAN", "parent d'élèves", "je ne travaille pas dans un établissement"],
)
def test_additional_information_form_asks_everything_of_who_works_elsewhere(job_title):
    form = ProAdditionalInformationForm(workshop=_workshop(job_title=job_title))
    assert len(form.fields) == 5
    assert form["postal_code"].value() is None


def test_additional_information_form_suggests_the_postal_code_of_the_school():
    form = ProAdditionalInformationForm(initial={}, workshop=_workshop())
    assert form["postal_code"].value() == "75005"


def test_additional_information_form_keeps_the_postal_code_she_already_gave():
    form = ProAdditionalInformationForm(initial={"postal_code": "75011"}, workshop=_workshop())
    assert form["postal_code"].value() == "75011"


def _pro(**overrides):
    return Pro(
        **{
            "structure_type": "company",
            "structure_name": "Inria",
            "job_title": "Chercheuse",
            "phone": "+33612345678",
            "postal_code": "75011",
            **overrides,
        }
    )


def _asked(form):
    return set(form.fields)


def test_additional_information_form_asks_nothing_she_already_gave():
    form = ProAdditionalInformationForm(pro=_pro())
    assert _asked(form) == set()
    assert not form.asks_anything


def test_additional_information_form_only_asks_what_she_has_not_given():
    form = ProAdditionalInformationForm(data={"phone": "0698765432"}, pro=_pro(phone=""))
    assert _asked(form) == {"phone"}
    assert form.asks_anything
    assert form.is_valid()
    assert form.cleaned_data["structure_name"] == "Inria"
    assert str(form.cleaned_data["phone"]) == "+33698765432"


def test_additional_information_form_asks_the_type_of_the_structure_she_named():
    form = ProAdditionalInformationForm(pro=_pro(structure_type=""))
    assert _asked(form) == {"structure_type"}


def test_additional_information_form_requires_the_name_of_a_known_type_of_structure():
    form = ProAdditionalInformationForm(data={}, pro=_pro(structure_name=""))
    assert _asked(form) == {"structure_name"}
    assert not form.is_valid()
    assert "structure_name" in form.errors


def test_additional_information_form_asks_no_structure_name_without_a_structure():
    form = ProAdditionalInformationForm(pro=_pro(structure_type="retired", structure_name=""))
    assert not form.asks_anything


def test_additional_information_form_ignores_what_is_posted_for_what_she_already_gave():
    form = ProAdditionalInformationForm(
        data={"phone": "0698765432", "structure_name": "Ailleurs"}, pro=_pro(phone="")
    )
    assert form.is_valid()
    assert form.cleaned_data["structure_name"] == "Inria"


@pytest.mark.django_db
def test_additional_information_form_saves_her_answers_onto_her_profile(pro):
    pro.structure_type = ""
    pro.save()
    form = ProAdditionalInformationForm(data={"structure_type": "association"}, pro=pro)
    assert form.is_valid()

    form.save(pro)

    pro.refresh_from_db()
    assert pro.structure_type == "association"
    assert pro.structure_name == "Inria"
