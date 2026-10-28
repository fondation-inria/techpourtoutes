import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0067_jobposting"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="jobposting",
            name="category",
        ),
        migrations.RemoveField(
            model_name="jobposting",
            name="domain",
        ),
        migrations.AddField(
            model_name="jobposting",
            name="categories",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("higher_ed_internship", "Stage du supérieur"),
                        ("apprenticeship", "Alternance"),
                        ("seconde_internship", "Stage de seconde"),
                        ("troisieme_internship", "Stage de troisième"),
                        ("first_job", "Premier emploi"),
                    ],
                    max_length=20,
                ),
                default=list,
                size=None,
                verbose_name="catégories",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="jobposting",
            name="domains",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=255),
                default=list,
                size=None,
                verbose_name="domaines",
            ),
            preserve_default=False,
        ),
    ]
