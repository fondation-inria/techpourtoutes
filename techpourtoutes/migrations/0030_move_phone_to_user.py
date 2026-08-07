import phonenumber_field.modelfields
from django.db import migrations


def copy_phone_to_user(apps, schema_editor):
    Pro = apps.get_model("techpourtoutes", "Pro")
    for pro in Pro.objects.exclude(phone=""):
        pro.user_ptr.phone_migration = pro.phone
        pro.user_ptr.save(update_fields=["phone_migration"])


def copy_phone_to_pro(apps, schema_editor):
    Pro = apps.get_model("techpourtoutes", "Pro")
    for pro in Pro.objects.all():
        pro.phone = pro.user_ptr.phone_migration
        pro.save(update_fields=["phone"])


class Migration(migrations.Migration):

    dependencies = [
        ('techpourtoutes', '0029_move_postal_code_to_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='phone_migration',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, default='', max_length=128, region='FR'),
            preserve_default=False,
        ),
        migrations.RunPython(copy_phone_to_user, copy_phone_to_pro),
        migrations.RemoveField(
            model_name='pro',
            name='phone',
        ),
        migrations.RenameField(
            model_name='user',
            old_name='phone_migration',
            new_name='phone',
        ),
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, region='FR', verbose_name='téléphone'),
        ),
    ]
