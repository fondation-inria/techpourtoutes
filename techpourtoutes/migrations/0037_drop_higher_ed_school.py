from django.db import migrations, models


class Migration(migrations.Migration):
    """Drop what the merge in 0036 made redundant, once its rows are committed."""

    dependencies = [
        ("techpourtoutes", "0036_merge_schools_add_formations"),
    ]

    operations = [
        migrations.AlterField(
            model_name="school",
            name="onisep_id",
            field=models.CharField(max_length=20, unique=True, verbose_name="identifiant Onisep"),
        ),
        migrations.RemoveField(model_name="school", name="identifier"),
        migrations.RemoveField(model_name="trainingexperience", name="higher_ed_school"),
        migrations.DeleteModel(name="HigherEdSchool"),
    ]
