import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0067_jobposting"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="jobposting",
            name="domain",
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
