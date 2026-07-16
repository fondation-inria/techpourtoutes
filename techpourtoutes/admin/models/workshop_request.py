from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models import WorkshopRequest


class WorkshopRequestInline(admin.TabularInline):
    model = WorkshopRequest
    can_delete = False
    fields = ("remark", "created_at")
    readonly_fields = ("remark", "created_at")
    verbose_name_plural = _("demandes d'atelier")

    def has_add_permission(self, _request, _obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-created_at")
