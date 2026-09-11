from techpourtoutes.forms.event import EventSubcategoryForm
from techpourtoutes.models import Event


def test_a_listed_subcategory_is_stored_as_its_key():
    form = EventSubcategoryForm(data={"subcategory": Event.Subcategory.HACKATHON})

    assert form.is_valid()
    assert form.resolved_subcategory == "hackathon"


def test_the_other_subcategory_is_stored_as_the_free_text():
    """ "Autre" is a prompt, not a value: what the user typed is what gets saved."""
    form = EventSubcategoryForm(
        data={
            "subcategory": Event.Subcategory.OTHER,
            "subcategory_other": "Rencontre d'anciennes élèves",
        }
    )

    assert form.is_valid()
    assert form.resolved_subcategory == "Rencontre d'anciennes élèves"


def test_the_other_subcategory_demands_its_free_text():
    form = EventSubcategoryForm(
        data={"subcategory": Event.Subcategory.OTHER, "subcategory_other": ""}
    )

    assert not form.is_valid()
    assert "subcategory_other" in form.errors


def test_a_free_text_left_over_from_another_subcategory_is_ignored():
    form = EventSubcategoryForm(
        data={
            "subcategory": Event.Subcategory.SALON,
            "subcategory_other": "Rencontre d'anciennes",
        }
    )

    assert form.is_valid()
    assert form.resolved_subcategory == "salon"


def test_a_subcategory_is_required():
    assert not EventSubcategoryForm(data={}).is_valid()
