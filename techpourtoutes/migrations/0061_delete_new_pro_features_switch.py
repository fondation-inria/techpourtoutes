from django.db import migrations

SWITCH_NAME = "new_pro_features"


def delete_switch(apps, schema_editor):
    Switch = apps.get_model("waffle", "Switch")
    Switch.objects.filter(name=SWITCH_NAME).delete()


def create_switch(apps, schema_editor):
    Switch = apps.get_model("waffle", "Switch")
    Switch.objects.get_or_create(
        name=SWITCH_NAME,
        defaults={"active": False, "note": "Nouvelles fonctionnalités pros"},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0060_pro_structure_type_and_mobilize_structure"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(delete_switch, create_switch),
    ]
