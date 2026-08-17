from django.db import migrations, models


class Migration(migrations.Migration):
    """Split from 0043: adding these constraints in the same transaction as its data
    UPDATE fails on PostgreSQL with "cannot ALTER TABLE because it has pending trigger
    events" — the ADD CONSTRAINT needs the prior UPDATE's trigger queue flushed first.
    """

    dependencies = [
        ("techpourtoutes", "0043_training_experience_out_of_scope_names"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="trainingexperience",
            constraint=models.CheckConstraint(
                condition=models.Q(school__isnull=False) ^ ~models.Q(out_of_scope_school_name=""),
                name="school_xor_out_of_scope_school_name",
                violation_error_message="Renseignez soit un établissement, soit son nom.",
            ),
        ),
        migrations.AddConstraint(
            model_name="trainingexperience",
            constraint=models.CheckConstraint(
                condition=models.Q(formation__isnull=False)
                ^ ~models.Q(out_of_scope_formation_name=""),
                name="formation_xor_out_of_scope_formation_name",
                violation_error_message="Renseignez soit une formation, soit son nom.",
            ),
        ),
    ]
