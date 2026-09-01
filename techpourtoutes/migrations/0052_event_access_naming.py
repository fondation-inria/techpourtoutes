from django.db import migrations, models


class Migration(migrations.Migration):
    """Renames written by hand: `makemigrations` cannot ask about a rename without a TTY and
    falls back to Remove + Add, which would drop whatever the column already holds.

    `HistoricalEvent` carries the same fields, so every operation comes in a pair.
    """

    dependencies = [
        ("techpourtoutes", "0051_create_event"),
    ]

    ACCESS_CHOICES = [
        ("open", "Accès libre"),
        ("registration", "Inscription obligatoire"),
        ("candidacy", "Sur candidature"),
    ]

    operations = [
        migrations.RenameField(
            model_name="event", old_name="event_url", new_name="registration_url"
        ),
        migrations.RenameField(
            model_name="historicalevent", old_name="event_url", new_name="registration_url"
        ),
        migrations.AlterField(
            model_name="event",
            name="registration_url",
            field=models.URLField(blank=True, verbose_name="lien d'inscription"),
        ),
        migrations.AlterField(
            model_name="historicalevent",
            name="registration_url",
            field=models.URLField(blank=True, verbose_name="lien d'inscription"),
        ),
        migrations.AlterField(
            model_name="event",
            name="access_type",
            field=models.CharField(
                choices=ACCESS_CHOICES, max_length=20, verbose_name="modalité d'inscription"
            ),
        ),
        migrations.AlterField(
            model_name="historicalevent",
            name="access_type",
            field=models.CharField(
                choices=ACCESS_CHOICES, max_length=20, verbose_name="modalité d'inscription"
            ),
        ),
        migrations.AddConstraint(
            model_name="event",
            constraint=models.CheckConstraint(
                condition=~models.Q(status="approved", location_type="physical")
                | models.Q(latitude__isnull=False, longitude__isnull=False),
                name="approved_physical_event_is_geocoded",
                violation_error_message=(
                    "Un événement en présentiel doit être géocodé avant d'être validé."
                ),
            ),
        ),
    ]
