from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('techpourtoutes', '0026_trainingexperience_ordering_and_unique_period'),
    ]

    operations = [
        migrations.AddField(
            model_name='beneficiary',
            name='birth_date',
            field=models.DateField(blank=True, null=True, verbose_name='date de naissance'),
        ),
    ]
