from techpourtoutes.forms import ProWorkshopRequestForm


def _workshop_request(**overrides):
    answers = {
        "job_title": "Enseignante",
        "structure_uai": "0750001A",
        "school_label": "Lycée Voltaire",
        "postal_code": "75011",
        "ateliers": ["future_of_tech", "future_of_ia"],
        **overrides,
    }
    return {f"workshop-{name}": value for name, value in answers.items()}


def test_workshop_request_form_accepts_a_school_picked_in_the_list():
    form = ProWorkshopRequestForm(data=_workshop_request())
    assert form.is_valid()
    assert form.cleaned_data["ateliers"] == ["future_of_tech", "future_of_ia"]


def test_workshop_request_form_ignores_the_answers_of_the_other_screens():
    form = ProWorkshopRequestForm(
        data={**_workshop_request(), "job_title": "Chercheuse", "school_not_found": "on"}
    )
    assert form.is_valid()
    assert form.cleaned_data["job_title"] == "Enseignante"
    assert form.school_not_found is False


def test_workshop_request_form_requires_a_school_picked_in_the_list():
    form = ProWorkshopRequestForm(data=_workshop_request(structure_uai=""))
    assert not form.is_valid()
    assert "school_label" in form.errors


def test_workshop_request_form_accepts_a_school_missing_from_the_list():
    form = ProWorkshopRequestForm(data=_workshop_request(structure_uai="", school_not_found="on"))
    assert form.is_valid()


def test_workshop_request_form_requires_a_workshop():
    form = ProWorkshopRequestForm(data=_workshop_request(ateliers=[]))
    assert not form.is_valid()
    assert "ateliers" in form.errors
