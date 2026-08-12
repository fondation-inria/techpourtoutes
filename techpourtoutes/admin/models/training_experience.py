from techpourtoutes.models import TrainingExperience

from ..read_only import ReadOnlyTabularInline


class TrainingExperienceInline(ReadOnlyTabularInline):
    model = TrainingExperience
    fields = ("school", "formation", "level", "start_date", "end_date")
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("school", "formation")
