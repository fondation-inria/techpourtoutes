import pytest

from techpourtoutes.forms import ProEngagementsForm


def test_engagements_form_requires_at_least_one_engagement():
    form = ProEngagementsForm(data={"engagements": []})
    assert not form.is_valid()
    assert "engagements" in form.errors


def test_engagements_form_offers_events_and_other_alongside_the_engagements():
    form = ProEngagementsForm(
        data={
            "engagements": ["mentor", "mobilize_structure", "events", "other"],
            "message": "Je veux aider.",
        }
    )
    assert form.is_valid()


def test_engagements_form_keeps_the_message_when_other_is_checked():
    form = ProEngagementsForm(data={"engagements": ["other"], "message": "Je veux aider."})
    assert form.is_valid()
    assert form.cleaned_data["message"] == "Je veux aider."


def test_engagements_form_requires_the_message_when_other_is_checked():
    form = ProEngagementsForm(data={"engagements": ["mentor", "other"], "message": ""})
    assert not form.is_valid()
    assert "message" in form.errors


def test_engagements_form_drops_the_message_when_other_is_not_checked():
    form = ProEngagementsForm(data={"engagements": ["mentor"], "message": "Je veux aider."})
    assert form.is_valid()
    assert form.cleaned_data["message"] == ""


def test_engagements_form_limits_the_message_to_1000_characters():
    form = ProEngagementsForm(data={"engagements": ["other"], "message": "a" * 1001})
    assert not form.is_valid()
    assert "message" in form.errors


@pytest.mark.parametrize("other", ["mentor", "workshops", "other"])
def test_engagements_form_keeps_a_training_ambassador_apart_from_the_other_engagements(other):
    form = ProEngagementsForm(
        data={"engagements": ["training_ambassador", other], "message": "Je veux aider."}
    )
    assert not form.is_valid()
    assert "engagements" in form.errors


def test_engagements_form_lets_a_training_ambassador_propose_events():
    form = ProEngagementsForm(data={"engagements": ["training_ambassador", "events"]})
    assert form.is_valid()
