from .school_year import current_school_year_start_date


def training_experience_slots(training_experiences):
    """Experiences plus a placeholder (None) for a missing current year, sorted for display."""
    slots = list(training_experiences)
    if not any(experience.is_current_school_year for experience in slots):
        slots.append(None)
    return sorted(slots, key=_slot_start_date, reverse=True)


def training_experience_insertion_anchor(beneficiary, start_date, exclude_pk=None):
    """Id of the slot to insert before an experience with this start date, or None to append."""
    siblings = beneficiary.training_experiences.all()
    if exclude_pk is not None:
        siblings = siblings.exclude(pk=exclude_pk)
    for slot in training_experience_slots(siblings):
        if _slot_start_date(slot) < start_date:
            return slot.pk if slot else "current-year"
    return None


def _slot_start_date(experience):
    return experience.start_date if experience is not None else current_school_year_start_date()
