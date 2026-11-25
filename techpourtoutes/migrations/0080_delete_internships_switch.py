from django.db import migrations

SWITCH_NAME = "internships"


def delete_switch(apps, schema_editor):
    Switch = apps.get_model("waffle", "Switch")
    Switch.objects.filter(name=SWITCH_NAME).delete()


def create_switch(apps, schema_editor):
    Switch = apps.get_model("waffle", "Switch")
    Switch.objects.get_or_create(
        name=SWITCH_NAME,
        defaults={"active": False, "note": "Affichage des stages"},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0079_jobposting_without_pmsmp_and_electrotechnique"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(delete_switch, create_switch),
    ]
