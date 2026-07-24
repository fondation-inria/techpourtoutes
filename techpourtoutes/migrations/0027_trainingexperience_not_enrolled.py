from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('techpourtoutes', '0026_trainingexperience_ordering_and_unique_period'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainingexperience',
            name='course',
            field=models.CharField(blank=True, max_length=255, verbose_name='cursus'),
        ),
    ]
