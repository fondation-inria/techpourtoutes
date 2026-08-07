from datetime import date

from techpourtoutes.utils.school_year import current_school_year_start_date, school_year_choices


def test_current_school_year_start_date_before_rollover_month(monkeypatch):
    monkeypatch.setattr(
        "techpourtoutes.utils.school_year.timezone.localdate",
        lambda: date(2026, 3, 15),
    )

    assert current_school_year_start_date() == date(2025, 9, 1)


def test_current_school_year_start_date_after_rollover_month(monkeypatch):
    monkeypatch.setattr(
        "techpourtoutes.utils.school_year.timezone.localdate",
        lambda: date(2026, 9, 1),
    )

    assert current_school_year_start_date() == date(2026, 9, 1)


def test_school_year_choices_ranges_from_ten_years_back_to_next_year(monkeypatch):
    monkeypatch.setattr(
        "techpourtoutes.utils.school_year.timezone.localdate",
        lambda: date(2026, 3, 15),
    )

    choices = school_year_choices()

    assert choices[0] == ("2026-2027", "2026-2027")
    assert choices[-1] == ("2015-2016", "2015-2016")
    assert len(choices) == 12
