import unicodedata

import django.db.models.deletion
from django.db import migrations, models


def normalize(value):
    """Local copy of `strip_accents`: a migration must not import application code."""
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value or "")
        if not unicodedata.combining(char)
    )


def capitalize_first(value):
    """Local copy of `capitalize_first`, same reason."""
    return (value or "")[:1].upper() + (value or "")[1:]


def capitalize_and_normalize_names(apps, schema_editor):
    """Align the rows imported before the mapper started doing it itself."""
    Formation = apps.get_model("techpourtoutes", "Formation")
    formations = list(Formation.objects.only("id", "name"))
    for formation in formations:
        formation.name = capitalize_first(formation.name)
        formation.name_normalized = normalize(formation.name)
    Formation.objects.bulk_update(formations, ["name", "name_normalized"], batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0039_alter_school_cog_code_alter_school_parent_onisep_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="formation",
            name="name_normalized",
            field=models.CharField(blank=True, editable=False, max_length=255),
        ),
        migrations.AddField(
            model_name="trainingexperience",
            name="formation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="training_experiences",
                to="techpourtoutes.formation",
                verbose_name="formation",
            ),
        ),
        migrations.AlterField(
            model_name="formationaction",
            name="onisep_id",
            field=models.CharField(
                blank=True, max_length=20, null=True, unique=True, verbose_name="identifiant Onisep"
            ),
        ),
        migrations.AlterField(
            model_name="school",
            name="parent_onisep_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=20,
                verbose_name="identifiant Onisep de l'université de rattachement",
            ),
        ),
        migrations.AlterField(
            model_name="trainingexperience",
            name="course",
            field=models.CharField(blank=True, max_length=255, verbose_name="filière"),
        ),
        migrations.RunPython(capitalize_and_normalize_names, migrations.RunPython.noop),
    ]
