from django.db import migrations

SWITCH_NAME = "discord"


def create_switch(apps, schema_editor):
    Switch = apps.get_model("waffle", "Switch")
    Switch.objects.get_or_create(
        name=SWITCH_NAME,
        defaults={"active": False, "note": "Accès des bénéficiaires au serveur Discord"},
    )


def delete_switch(apps, schema_editor):
    Switch = apps.get_model("waffle", "Switch")
    Switch.objects.filter(name=SWITCH_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0081_beneficiary_discord_user_id"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(create_switch, delete_switch),
    ]
