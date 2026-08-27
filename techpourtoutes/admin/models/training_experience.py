from techpourtoutes.models import TrainingExperience

from ..read_only import ReadOnlyTabularInline


class TrainingExperienceInline(ReadOnlyTabularInline):
    model = TrainingExperience
    fields = (
        "school",
        "out_of_scope_school_name",
        "formation",
        "out_of_scope_formation_name",
        "level",
        "start_date",
        "end_date",
    )
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("school", "formation")
