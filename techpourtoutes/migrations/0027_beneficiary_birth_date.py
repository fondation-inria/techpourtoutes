import django.db.models.deletion
import techpourtoutes.models.user
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('techpourtoutes', '0026_trainingexperience_ordering_and_unique_period'),
    ]

    operations = [
        migrations.CreateModel(
            name='Beneficiary',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'bénéficiaire',
                'verbose_name_plural': 'bénéficiaires',
            },
            bases=('techpourtoutes.user',),
            managers=[
                ('objects', techpourtoutes.models.user.ActiveUserManager()),
            ],
        ),
        migrations.AddField(
            model_name='beneficiary',
            name='birth_date',
            field=models.DateField(blank=True, null=True, verbose_name='date de naissance'),
        ),
    ]
