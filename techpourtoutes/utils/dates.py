from datetime import date


def compute_age(birth_date):
    today = date.today()
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def adult_birth_date():
    """Born later than this and you are still a minor today.

    ISO dates compare lexicographically, so the client can settle minority against this cutoff
    with a plain string comparison instead of redoing `compute_age` in JavaScript.
    """
    today = date.today()
    try:
        return today.replace(year=today.year - 18)
    except ValueError:  # 29 February
        return today.replace(year=today.year - 18, day=28)
