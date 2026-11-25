from django.db import migrations, models

DEPARTMENT_CODES = {f"{number:02d}" for number in range(1, 96) if number != 20} | {
    "2A",
    "2B",
    *("971", "972", "973", "974", "975", "976", "977", "978", "986", "987", "988"),
    "99",
}
CORSICA_POSTAL_CODES = {
    "200": "2A",
    "201": "2A",
    "202": "2B",
    "203": "2B",
    "204": "2B",
    "205": "2B",
    "206": "2B",
}


def department_code(cog_code, postal_code):
    code = cog_code or CORSICA_POSTAL_CODES.get(postal_code[:3], postal_code)
    department = code[:3] if code.startswith(("97", "98")) else code[:2]
    return department if department in DEPARTMENT_CODES else ""


def derive_department_codes(apps, schema_editor):
    Event = apps.get_model("techpourtoutes", "Event")
    events = list(Event.objects.only("cog_code", "postal_code"))
    for event in events:
        event.department_code = department_code(event.cog_code, event.postal_code)
    Event.objects.bulk_update(events, ["department_code"])


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0080_delete_internships_switch"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="department_code",
            field=models.CharField(
                blank=True, db_index=True, max_length=3, verbose_name="code du département"
            ),
        ),
        migrations.AddField(
            model_name="historicalevent",
            name="department_code",
            field=models.CharField(
                blank=True, db_index=True, max_length=3, verbose_name="code du département"
            ),
        ),
        migrations.RunPython(derive_department_codes, migrations.RunPython.noop),
    ]
