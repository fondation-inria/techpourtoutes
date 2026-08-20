from django.db import migrations, models


def copy_faveod_id_to_user(apps, schema_editor):
    Pro = apps.get_model("techpourtoutes", "Pro")
    # _base_manager and not .objects: ActiveUserManager sets use_in_migrations, so the
    # historical manager filters on is_active and would skip deactivated accounts.
    for pro in Pro._base_manager.exclude(faveod_id=None):
        pro.user_ptr.faveod_id_migration = pro.faveod_id
        pro.user_ptr.save(update_fields=["faveod_id_migration"])


def copy_faveod_id_to_pro(apps, schema_editor):
    Pro = apps.get_model("techpourtoutes", "Pro")
    for pro in Pro._base_manager.all():
        pro.faveod_id = pro.user_ptr.faveod_id_migration
        pro.save(update_fields=["faveod_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("techpourtoutes", "0046_beneficiary_legal_representative_name"),
    ]

    # Temporary field name: User.faveod_id and Pro.faveod_id may never coexist in the
    # migration state, as rendering it raises FieldError on the multi-table inheritance.
    operations = [
        migrations.AddField(
            model_name="user",
            name="faveod_id_migration",
            field=models.IntegerField(
                blank=True, null=True, unique=True, verbose_name="identifiant faveod"
            ),
        ),
        migrations.RunPython(copy_faveod_id_to_user, copy_faveod_id_to_pro),
        migrations.RemoveField(model_name="pro", name="faveod_id"),
        migrations.RenameField(
            model_name="user", old_name="faveod_id_migration", new_name="faveod_id"
        ),
    ]
