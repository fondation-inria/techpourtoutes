from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('techpourtoutes', '0025_beneficiary_and_training_experience'),
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
