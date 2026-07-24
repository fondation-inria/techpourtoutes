import django.core.validators
from django.db import migrations, models


def copy_postal_code_to_user(apps, schema_editor):
    Pro = apps.get_model("techpourtoutes", "Pro")
    for pro in Pro.objects.exclude(postal_code=""):
        pro.user_ptr.postal_code_migration = pro.postal_code
        pro.user_ptr.save(update_fields=["postal_code_migration"])


def copy_postal_code_to_pro(apps, schema_editor):
    Pro = apps.get_model("techpourtoutes", "Pro")
    for pro in Pro.objects.all():
        pro.postal_code = pro.user_ptr.postal_code_migration
        pro.save(update_fields=["postal_code"])


class Migration(migrations.Migration):

    dependencies = [
        ('techpourtoutes', '0028_beneficiary_birth_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='postal_code_migration',
            field=models.CharField(blank=True, default='', max_length=5, validators=[django.core.validators.RegexValidator('^\\d{5}$', 'Entrez un code postal valide à 5 chiffres.')]),
            preserve_default=False,
        ),
        migrations.RunPython(copy_postal_code_to_user, copy_postal_code_to_pro),
        migrations.RemoveField(
            model_name='pro',
            name='postal_code',
        ),
        migrations.RenameField(
            model_name='user',
            old_name='postal_code_migration',
            new_name='postal_code',
        ),
        migrations.AlterField(
            model_name='user',
            name='postal_code',
            field=models.CharField(blank=True, max_length=5, validators=[django.core.validators.RegexValidator('^\\d{5}$', 'Entrez un code postal valide à 5 chiffres.')], verbose_name='code postal'),
        ),
    ]
