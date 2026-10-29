from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0068_jobposting_categories_domains"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobposting",
            name="hidden",
            field=models.BooleanField(
                default=False,
                help_text="Une offre dépubliée n'apparaît plus sur le site. Décocher la republie.",
                verbose_name="dépubliée",
            ),
        ),
    ]
