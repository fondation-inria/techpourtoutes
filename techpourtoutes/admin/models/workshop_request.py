from django.utils.translation import gettext_lazy as _

from techpourtoutes.models import WorkshopRequest

from ..read_only import ReadOnlyTabularInline


class WorkshopRequestInline(ReadOnlyTabularInline):
    model = WorkshopRequest
    fields = ("type", "remark", "created_at")
    readonly_fields = ("type", "remark", "created_at")
    verbose_name_plural = _("demandes d'atelier")

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-created_at")
