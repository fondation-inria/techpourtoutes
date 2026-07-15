from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models import Pro


def _toggle(values, value):
    return [v for v in values if v != value] if value in values else [*values, value]


class EngagementFilter(admin.SimpleListFilter):
    # Multi-select filter: several engagements can be checked at once. Values ride in a single
    # comma-separated GET param and match with PostgreSQL `overlap` (any of the selected ones).
    title = _("engagement")
    parameter_name = "engagement"
    template = "admin/includes/engagement_filter.html"

    def __init__(self, request, params, model, model_admin):
        self.request = request
        super().__init__(request, params, model, model_admin)

    def lookups(self, request, model_admin):
        return Pro.Engagement.choices

    def has_output(self):
        return True

    @property
    def _selected(self):
        raw = self.request.GET.get(self.parameter_name, "")
        return [value for value in raw.split(",") if value]

    def queryset(self, request, queryset):
        return queryset.filter(engagements__overlap=self._selected) if self._selected else queryset

    def choices(self, changelist):
        selected = self._selected
        for value, label in self.lookup_choices:
            toggled = _toggle(selected, value)
            query_string = (
                changelist.get_query_string({self.parameter_name: ",".join(toggled)})
                if toggled
                else changelist.get_query_string(remove=[self.parameter_name])
            )
            yield {"selected": value in selected, "query_string": query_string, "display": label}
