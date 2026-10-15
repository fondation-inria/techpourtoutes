from django.db import migrations

WITHOUT_STRUCTURE = ("retired", "jobless")


# The situation is only kept where no structure type says it yet: a retired or jobless one
# carries over as such, and a student — a training ambassador — studies at the school of her
# parcours.
def infer_structure_type(apps, schema_editor):
    Pro = apps.get_model("techpourtoutes", "Pro")
    TrainingExperience = apps.get_model("techpourtoutes", "TrainingExperience")
    for situation in WITHOUT_STRUCTURE:
        Pro.objects.filter(professional_situation=situation, structure_type="").update(
            structure_type=situation
        )
    for student in Pro.objects.filter(professional_situation="student", structure_type=""):
        experience = (
            TrainingExperience.objects.filter(user_id=student.pk)
            .select_related("school")
            .order_by("-start_date")
            .first()
        )
        student.structure_type = "higher_ed"
        student.structure_name = _school_name(experience)
        student.save(update_fields=["structure_type", "structure_name"])


def _school_name(experience):
    if experience is None:
        return ""
    return experience.school.name if experience.school else experience.out_of_scope_school_name


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0061_delete_new_pro_features_switch"),
    ]

    operations = [
        migrations.RunPython(infer_structure_type, migrations.RunPython.noop),
        migrations.RemoveField(model_name="pro", name="professional_situation"),
    ]
