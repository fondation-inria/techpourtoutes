from datetime import date

from django.utils import timezone

SCHOOL_YEAR_ROLLOVER_MONTH = 8


def school_year_label(start_date, end_date):
    return f"{start_date.year}-{end_date.year}"


def school_year_dates(period_label):
    start_year, end_year = (int(year) for year in period_label.split("-"))
    return date(start_year, 9, 1), date(end_year, 8, 31)


def current_school_year_start_date():
    today = timezone.localdate()
    start_year = today.year if today.month > SCHOOL_YEAR_ROLLOVER_MONTH else today.year - 1
    return date(start_year, 9, 1)


def next_school_year_start_date():
    return date(current_school_year_start_date().year + 1, 9, 1)


def current_school_year_end_date():
    return date(current_school_year_start_date().year + 1, 8, 31)


def current_school_year_label():
    start_date = current_school_year_start_date()
    return school_year_label(start_date, date(start_date.year + 1, 8, 31))


def school_year_choices(years_back=10, years_forward=1):
    current_start_year = current_school_year_start_date().year
    return [
        (
            school_year_label(date(year, 9, 1), date(year + 1, 8, 31)),
            school_year_label(date(year, 9, 1), date(year + 1, 8, 31)),
        )
        for year in reversed(
            range(current_start_year - years_back, current_start_year + years_forward + 1)
        )
    ]
