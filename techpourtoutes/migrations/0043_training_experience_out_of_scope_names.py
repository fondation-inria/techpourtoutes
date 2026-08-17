from django.db import migrations, models


def enforce_one_side_only(apps, schema_editor):
    """Bring the existing rows in line with the constraints added right after.

    The renamed `course` covers the parcours left without a formation, but a row can carry both
    it and a linked formation — the link wins, as it does on every save from now on. The two
    empty cases cannot happen on the databases we know, so the fallback labels are a guard
    against an unknown row blocking the deployment, not a backfill.
    """
    TrainingExperience = apps.get_model("techpourtoutes", "TrainingExperience")
    TrainingExperience.objects.filter(formation__isnull=False).exclude(
        out_of_scope_formation_name=""
    ).update(out_of_scope_formation_name="")
    TrainingExperience.objects.filter(school__isnull=True, out_of_scope_school_name="").update(
        out_of_scope_school_name="Établissement non renseigné"
    )
    TrainingExperience.objects.filter(
        formation__isnull=True, out_of_scope_formation_name=""
    ).update(out_of_scope_formation_name="Formation non renseignée")


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0042_formation_higher_ed_formation_secondary"),
    ]

    operations = [
        migrations.RenameField(
            model_name="trainingexperience",
            old_name="course",
            new_name="out_of_scope_formation_name",
        ),
        migrations.AlterField(
            model_name="trainingexperience",
            name="out_of_scope_formation_name",
            field=models.CharField(
                blank=True, max_length=255, verbose_name="nom de la formation hors catalogue"
            ),
        ),
        migrations.AddField(
            model_name="trainingexperience",
            name="out_of_scope_school_name",
            field=models.CharField(
                blank=True, max_length=350, verbose_name="nom de l'établissement hors catalogue"
            ),
        ),
        migrations.RunPython(enforce_one_side_only, migrations.RunPython.noop),
    ]
