from django.contrib import admin

from techpourtoutes.models import Formation

from ..read_only import ReadOnlyAdminMixin
from ..stats import formation_stats
from .formation_action import TeachingSchoolInline


@admin.register(Formation)
class FormationAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "acronym",
        "type_name",
        "exit_level",
        "duration_in_years",
        "secondary",
        "higher_ed",
    )
    list_display_links = list_display
    search_fields = ("name", "acronym", "onisep_id")
    list_filter = ("exit_level", "secondary", "higher_ed")
    inlines = [TeachingSchoolInline]

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), "stats": formation_stats()}
        return super().changelist_view(request, extra_context=extra_context)
