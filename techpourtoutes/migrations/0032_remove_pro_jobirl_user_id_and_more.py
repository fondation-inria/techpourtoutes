from django.db import migrations, models


def copy_jobirl_fields_to_user(apps, schema_editor):
    Pro = apps.get_model("techpourtoutes", "Pro")
    for pro in Pro.objects.exclude(jobirl_user_id=None):
        pro.user_ptr.jobirl_user_id_migration = pro.jobirl_user_id
        pro.user_ptr.jobirl_user_token_migration = pro.jobirl_user_token
        pro.user_ptr.save(
            update_fields=["jobirl_user_id_migration", "jobirl_user_token_migration"]
        )


def copy_jobirl_fields_to_pro(apps, schema_editor):
    Pro = apps.get_model("techpourtoutes", "Pro")
    for pro in Pro.objects.all():
        pro.jobirl_user_id = pro.user_ptr.jobirl_user_id_migration
        pro.jobirl_user_token = pro.user_ptr.jobirl_user_token_migration
        pro.save(update_fields=["jobirl_user_id", "jobirl_user_token"])


class Migration(migrations.Migration):

    dependencies = [
        ('techpourtoutes', '0031_alter_higheredschool_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='jobirl_user_id_migration',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='jobirl_user_token_migration',
            field=models.CharField(blank=True, default='', max_length=128),
            preserve_default=False,
        ),
        migrations.RunPython(copy_jobirl_fields_to_user, copy_jobirl_fields_to_pro),
        migrations.RemoveField(
            model_name='pro',
            name='jobirl_user_id',
        ),
        migrations.RemoveField(
            model_name='pro',
            name='jobirl_user_token',
        ),
        migrations.RenameField(
            model_name='user',
            old_name='jobirl_user_id_migration',
            new_name='jobirl_user_id',
        ),
        migrations.RenameField(
            model_name='user',
            old_name='jobirl_user_token_migration',
            new_name='jobirl_user_token',
        ),
        migrations.AlterField(
            model_name='user',
            name='jobirl_user_id',
            field=models.BigIntegerField(blank=True, null=True, verbose_name='identifiant utilisateur jobirl'),
        ),
        migrations.AlterField(
            model_name='user',
            name='jobirl_user_token',
            field=models.CharField(blank=True, max_length=128, verbose_name='token utilisateur jobirl'),
        ),
    ]
