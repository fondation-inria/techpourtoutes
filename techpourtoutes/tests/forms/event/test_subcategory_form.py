import pytest

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
            "subcategory_other": "Rencontre entre elles",
        }
    )

    assert form.is_valid()
    assert form.resolved_subcategory == "Rencontre entre elles"


def test_the_other_subcategory_free_text_is_capped_at_22_characters():
    form = EventSubcategoryForm(
        data={
            "subcategory": Event.Subcategory.OTHER,
            "subcategory_other": "Rencontre d'anciennes élèves",
        }
    )

    assert not form.is_valid()
    assert "subcategory_other" in form.errors


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


@pytest.mark.django_db
def test_the_form_prefilled_from_an_event_reads_a_listed_subcategory_straight_off_the_event(event):
    answers = EventSubcategoryForm(event=event).initial

    assert answers == {"subcategory": event.subcategory, "subcategory_other": ""}
    assert EventSubcategoryForm(data=answers).is_valid()


@pytest.mark.django_db
def test_the_form_prefilled_from_an_event_puts_an_unlisted_subcategory_back_under_other(pro):
    """The mirror of `resolved_subcategory`: the free text returns to the field it came from."""
    from ...models.test_event import build_event

    event = build_event(pro, subcategory="Rencontre d'anciennes élèves")
    event.save()

    form = EventSubcategoryForm(data=EventSubcategoryForm(event=event).initial)

    assert form.is_valid()
    assert form.resolved_subcategory == "Rencontre d'anciennes élèves"


def test_event_fields_carries_the_resolved_subcategory():
    form = EventSubcategoryForm(
        data={"subcategory": Event.Subcategory.OTHER, "subcategory_other": "Rencontre"}
    )

    assert form.is_valid()
    assert form.event_fields == {"subcategory": "Rencontre"}
