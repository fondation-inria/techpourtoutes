from techpourtoutes.models import SavedEvent

from ..read_only import ReadOnlyTabularInline


class BeneficiarySavedEventInline(ReadOnlyTabularInline):
    """On a beneficiary: what she put aside. Repeating her own name would teach nothing."""

    model = SavedEvent
    fields = ("event", "created_at")
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("event")


class EventSavedByInline(ReadOnlyTabularInline):
    """On an event: who put it aside."""

    model = SavedEvent
    fields = ("beneficiary", "created_at")
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("beneficiary")
