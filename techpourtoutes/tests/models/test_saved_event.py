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
