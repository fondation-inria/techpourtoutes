from datetime import date


def birth_date_for_age(age):
    """The birth date of someone turning `age` today."""
    today = date.today()
    try:
        return today.replace(year=today.year - age)
    except ValueError:  # 29 February
        return today.replace(year=today.year - age, day=28)
