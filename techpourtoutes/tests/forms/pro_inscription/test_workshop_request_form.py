import pytest

from techpourtoutes.forms import ProWorkshopRequestForm

pytestmark = pytest.mark.django_db


def _workshop_request(school, **overrides):
    answers = {
        "job_title": "Enseignante",
        "school_id": str(school.pk),
        "school_label": "Lycée Voltaire",
        "postal_code": "75011",
        "ateliers": ["future_of_tech", "future_of_ia"],
        **overrides,
    }
    return {f"workshop-{name}": value for name, value in answers.items()}


def test_workshop_request_form_accepts_a_school_picked_in_the_list(school):
    form = ProWorkshopRequestForm(data=_workshop_request(school))
    assert form.is_valid()
    assert form.cleaned_data["ateliers"] == ["future_of_tech", "future_of_ia"]
    assert form.school == school


def test_workshop_request_form_ignores_the_answers_of_the_other_screens(school):
    form = ProWorkshopRequestForm(
        data={**_workshop_request(school), "job_title": "Chercheuse", "school_not_found": "on"}
    )
    assert form.is_valid()
    assert form.cleaned_data["job_title"] == "Enseignante"
    assert form.school_not_found is False


def test_workshop_request_form_requires_a_school_picked_in_the_list(school):
    form = ProWorkshopRequestForm(data=_workshop_request(school, school_id=""))
    assert not form.is_valid()
    assert "school_label" in form.errors


def test_workshop_request_form_rejects_a_school_outside_the_secondary_ones(
    school, higher_ed_school
):
    form = ProWorkshopRequestForm(
        data=_workshop_request(school, school_id=str(higher_ed_school.pk))
    )
    assert not form.is_valid()
    assert form.errors["school_label"] == ["Sélectionnez un établissement dans la liste."]


def test_workshop_request_form_accepts_a_school_missing_from_the_list(school):
    form = ProWorkshopRequestForm(
        data=_workshop_request(school, school_id="", school_not_found="on")
    )
    assert form.is_valid()
    assert form.school is None


def test_workshop_request_form_requires_a_workshop(school):
    form = ProWorkshopRequestForm(data=_workshop_request(school, ateliers=[]))
    assert not form.is_valid()
    assert "ateliers" in form.errors


@pytest.mark.parametrize(
    "job_title,works_at_school",
    [
        ("Enseignante", True),
        ("Autre mission au sein d'un établissement", True),
        ("DRANE / DAN / IAN", False),
        ("parent d'élèves", False),
        ("je ne travaille pas dans un établissement", False),
    ],
)
def test_workshop_request_form_tells_whether_she_works_at_the_school(
    school, job_title, works_at_school
):
    form = ProWorkshopRequestForm(data=_workshop_request(school, job_title=job_title))
    assert form.is_valid()
    assert form.works_at_school is works_at_school
