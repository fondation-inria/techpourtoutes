import pytest
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_a_beneficiary_saves_an_event_only_once(event, beneficiary):
    from techpourtoutes.models import SavedEvent

    SavedEvent(event=event, beneficiary=beneficiary).save()

    with pytest.raises(ValidationError):
        SavedEvent(event=event, beneficiary=beneficiary).save()


@pytest.mark.django_db
def test_a_saved_event_is_reachable_from_both_sides(event, beneficiary):
    from techpourtoutes.models import SavedEvent

    save = SavedEvent(event=event, beneficiary=beneficiary)
    save.save()

    assert list(beneficiary.saved_events.all()) == [event]
    assert list(event.saves.all()) == [save]
    assert save.created_at is not None
    assert str(save) == "Jade PETIT – Salon des métiers du numérique"


@pytest.mark.django_db
def test_toggle_puts_an_event_aside_then_takes_it_back_out(event, beneficiary):
    from techpourtoutes.models import SavedEvent

    assert SavedEvent.objects.toggle(event=event, beneficiary=beneficiary) is True
    assert list(beneficiary.saved_events.all()) == [event]

    assert SavedEvent.objects.toggle(event=event, beneficiary=beneficiary) is False
    assert list(beneficiary.saved_events.all()) == []


@pytest.mark.django_db
def test_toggle_leaves_another_beneficiarys_save_alone(event, beneficiary):
    from techpourtoutes.models import Beneficiary, SavedEvent

    other = Beneficiary(
        username="lou@example.com", email="lou@example.com", first_name="Lou", last_name="Bernard"
    )
    other.save()
    SavedEvent.objects.toggle(event=event, beneficiary=other)

    SavedEvent.objects.toggle(event=event, beneficiary=beneficiary)
    SavedEvent.objects.toggle(event=event, beneficiary=beneficiary)

    assert list(other.saved_events.all()) == [event]
