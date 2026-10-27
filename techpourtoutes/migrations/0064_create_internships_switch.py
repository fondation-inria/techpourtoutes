from django.db import migrations

SWITCH_NAME = "internships"


def create_switch(apps, schema_editor):
    Switch = apps.get_model("waffle", "Switch")
    Switch.objects.get_or_create(
        name=SWITCH_NAME,
        defaults={"active": False, "note": "Affichage des stages"},
    )


def delete_switch(apps, schema_editor):
    Switch = apps.get_model("waffle", "Switch")
    Switch.objects.filter(name=SWITCH_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0063_makeuse_project"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(create_switch, delete_switch),
    ]
