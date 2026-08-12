from django.utils.translation import gettext_lazy as _

from techpourtoutes.models import FormationAction

from ..read_only import ReadOnlyTabularInline


class TaughtFormationInline(ReadOnlyTabularInline):
    """What the établissement teaches, on its own page."""

    model = FormationAction
    fields = ("formation",)
    readonly_fields = fields
    verbose_name_plural = _("formations proposées")

    def get_queryset(self, request):
        actions = super().get_queryset(request).select_related("formation")
        return actions.order_by("formation__name")


class TeachingSchoolInline(ReadOnlyTabularInline):
    """Where the formation is taught, on its own page."""

    model = FormationAction
    fields = ("school",)
    readonly_fields = fields
    verbose_name_plural = _("établissements proposant la formation")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("school").order_by("school__name")
