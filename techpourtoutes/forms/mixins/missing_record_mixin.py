from ...models import Level


class MissingRecordMixin:
    """The record the user is looking for is absent from the Onisep catalogue.

    Each flag turns its autocomplete into a free-text field: the id stops being submitted and
    the typed name becomes mandatory in its place. The two flags are independent — not finding
    the school says nothing about the formation, which is then searched catalogue-wide.
    The form declares the flags itself; a bare mixin cannot carry form fields.
    """

    _school = None
    _formation = None

    @property
    def school_not_found(self):
        return self.cleaned_data.get("school_not_found", False)

    @property
    def formation_not_found(self):
        return self.cleaned_data.get("formation_not_found", False)

    @property
    def has_missing_record(self):
        return self.school_not_found or self.formation_not_found

    @property
    def out_of_scope_school_name(self):
        return self.cleaned_data.get("school_label", "") if self.school_not_found else ""

    @property
    def out_of_scope_formation_name(self):
        return self.cleaned_data.get("formation_label", "") if self.formation_not_found else ""

    def missing_record_report(self):
        level = self.cleaned_data.get("level", "")
        return {
            "level": Level(level).label if level else "",
            "school_label": self.cleaned_data.get("school_label", ""),
            "formation_label": self.cleaned_data.get("formation_label", ""),
            "school": self._school,
            "formation": self._formation,
        }
