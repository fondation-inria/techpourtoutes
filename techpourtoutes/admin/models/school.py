from django.contrib import admin

from techpourtoutes.models import School

from ..read_only import ReadOnlyAdminMixin
from ..stats import school_stats
from .formation_action import TaughtFormationInline


@admin.register(School)
class SchoolAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("name", "acronym", "uai", "postal_code", "city", "secondary", "higher_ed")
    list_display_links = list_display
    search_fields = ("name", "acronym", "uai", "onisep_id")
    list_filter = ("secondary", "higher_ed", "training_ambassador_eligible", "recommended")
    inlines = [TaughtFormationInline]

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), "stats": school_stats()}
        return super().changelist_view(request, extra_context=extra_context)
