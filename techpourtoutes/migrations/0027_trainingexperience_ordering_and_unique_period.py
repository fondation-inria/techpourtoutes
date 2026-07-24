from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('techpourtoutes', '0026_trainingexperience_school_year_and_level'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='trainingexperience',
            options={
                'ordering': ['-start_date'],
                'verbose_name': 'formation',
                'verbose_name_plural': 'formations',
            },
        ),
        migrations.AddConstraint(
            model_name='trainingexperience',
            constraint=models.UniqueConstraint(
                fields=('user', 'start_date'), name='unique_user_start_date'
            ),
        ),
    ]
