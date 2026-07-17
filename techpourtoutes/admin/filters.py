from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models import Pro


class EngagementFilter(admin.SimpleListFilter):
    """
    Multi-select filter: several engagements can be checked at once, carried as a comma-separated
    GET param and matched with PostgreSQL `overlap` (any of the selected ones).

    Overrides SimpleListFilter — https://github.com/django/django/blob/main/django/contrib/admin/filters.py
      - lookups() and queryset() are required abstracts
      - __init__() extended to store self.request (not kept by the parent)
      - choices() reimplemented for multi-select (default renders a single active choice at a time)
    """

    title = _("engagement")
    parameter_name = "engagement"
    template = "admin/includes/engagement_filter.html"

    def __init__(self, request, params, model, model_admin):
        self.request = request
        super().__init__(request, params, model, model_admin)

    def lookups(self, _request, _model_admin):
        return Pro.Engagement.choices

    def queryset(self, _request, queryset):
        if self._active_values:
            return queryset.filter(engagements__overlap=self._active_values)
        return queryset

    def choices(self, changelist):
        for value, label in self.lookup_choices:
            yield {
                "selected": self._is_selected(value),
                "query_string": self._toggle_url(changelist, value),
                "display": label,
            }

    @property
    def _active_values(self):
        raw = self.request.GET.get(self.parameter_name, "")
        return [value for value in raw.split(",") if value]

    def _is_selected(self, value):
        return value in self._active_values

    def _toggle_url(self, changelist, value):
        new_selection = self._toggle(self._active_values, value)
        if new_selection:
            return changelist.get_query_string({self.parameter_name: ",".join(new_selection)})
        return changelist.get_query_string(remove=[self.parameter_name])

    @staticmethod
    def _toggle(values, value):
        return [v for v in values if v != value] if value in values else [*values, value]
