from django.db import migrations, models


def copy_civility_to_user(apps, schema_editor):
    Pro = apps.get_model("techpourtoutes", "Pro")
    for pro in Pro.objects.exclude(civility=""):
        pro.user_ptr.civility_migration = pro.civility
        pro.user_ptr.save(update_fields=["civility_migration"])


def copy_civility_to_pro(apps, schema_editor):
    Pro = apps.get_model("techpourtoutes", "Pro")
    for pro in Pro.objects.all():
        pro.civility = pro.user_ptr.civility_migration
        pro.save(update_fields=["civility"])


class Migration(migrations.Migration):

    dependencies = [
        ("techpourtoutes", "0032_remove_pro_jobirl_user_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="civility_migration",
            field=models.CharField(
                blank=True,
                default="",
                max_length=10,
                choices=[("Madame", "Madame"), ("Monsieur", "Monsieur")],
            ),
            preserve_default=False,
        ),
        migrations.RunPython(copy_civility_to_user, copy_civility_to_pro),
        migrations.RemoveField(
            model_name="pro",
            name="civility",
        ),
        migrations.RenameField(
            model_name="user",
            old_name="civility_migration",
            new_name="civility",
        ),
        migrations.AlterField(
            model_name="user",
            name="civility",
            field=models.CharField(
                blank=True,
                max_length=10,
                choices=[("Madame", "Madame"), ("Monsieur", "Monsieur")],
                verbose_name="civilité",
            ),
        ),
    ]
