import unicodedata
import uuid

import django.db.models.deletion
import phonenumber_field.modelfields
from django.db import migrations, models

LEVEL_CHOICES = [
    ("quatrieme", "Quatrième"),
    ("troisieme", "Troisième"),
    ("seconde", "Seconde"),
    ("premiere", "Première"),
    ("cap", "CAP ou équivalent"),
    ("cap_plus_1", "CAP ou équivalent + 1 an"),
    ("terminale", "Terminale"),
    ("bac_1", "Bac +1"),
    ("bac_2", "Bac +2"),
    ("bac_3", "Bac +3"),
    ("bac_4", "Bac +4"),
    ("bac_5", "Bac +5"),
    ("bac_5_plus", "Au-delà de bac +5"),
    ("bac_6", "Bac +6"),
    ("bac_7", "Bac +7"),
    ("bac_8", "Bac +8"),
    ("bac_9_plus", "Bac +9 et plus"),
]


def normalize(value):
    """Local copy of `strip_accents`: a migration must not import application code."""
    return "".join(
        char for char in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(char)
    )


def merge_schools(apps, schema_editor):
    """Fold `HigherEdSchool` into `School` without losing a single row.

    The Onisep rows do not exist yet — they arrive with the first import — so every school
    kept here is a legacy placeholder, marked by a `legacy-` identifier and left out of every
    search scope. `remap_training_experience_schools` repoints the parcours onto their Onisep
    counterpart afterwards and deletes the placeholders.
    """
    School = apps.get_model("techpourtoutes", "School")
    HigherEdSchool = apps.get_model("techpourtoutes", "HigherEdSchool")
    TrainingExperience = apps.get_model("techpourtoutes", "TrainingExperience")

    for index, school in enumerate(School.objects.all()):
        school.onisep_id = f"legacy-s-{index}"
        school.uai = school.identifier
        school.name_normalized = normalize(school.name)
        school.save(update_fields=["onisep_id", "uai", "name_normalized"])

    for index, higher_ed_school in enumerate(HigherEdSchool.objects.all()):
        school = School.objects.create(
            onisep_id=f"legacy-h-{index}",
            uai=higher_ed_school.uai,
            siret=higher_ed_school.siret,
            name=higher_ed_school.full_name,
            name_normalized=normalize(higher_ed_school.full_name),
            acronym=higher_ed_school.name,
            acronym_normalized=normalize(higher_ed_school.name),
        )
        TrainingExperience.objects.filter(higher_ed_school=higher_ed_school).update(school=school)


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0035_alter_trainingexperience_course"),
    ]

    operations = [
        # --- new School columns, still loose enough to accept the legacy rows
        migrations.AddField(
            model_name="school",
            name="onisep_id",
            field=models.CharField(default="", max_length=20, verbose_name="identifiant Onisep"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="school",
            name="uai",
            field=models.CharField(blank=True, max_length=20, verbose_name="UAI"),
        ),
        migrations.AddField(
            model_name="school",
            name="siret",
            field=models.CharField(blank=True, max_length=20, verbose_name="SIRET"),
        ),
        migrations.AddField(
            model_name="school",
            name="type",
            field=models.CharField(
                blank=True, max_length=100, verbose_name="type d'établissement"
            ),
        ),
        migrations.AddField(
            model_name="school",
            name="acronym",
            field=models.CharField(blank=True, max_length=50, verbose_name="sigle"),
        ),
        migrations.AddField(
            model_name="school",
            name="acronym_normalized",
            field=models.CharField(blank=True, editable=False, max_length=50),
        ),
        migrations.AddField(
            model_name="school",
            name="status",
            field=models.CharField(blank=True, max_length=30, verbose_name="statut"),
        ),
        migrations.AddField(
            model_name="school",
            name="parent_uai",
            field=models.CharField(
                blank=True, max_length=20, verbose_name="UAI de l'université de rattachement"
            ),
        ),
        migrations.AddField(
            model_name="school",
            name="parent_onisep_id",
            field=models.CharField(
                blank=True, max_length=20, verbose_name="identifiant Onisep de l'université"
            ),
        ),
        migrations.AddField(
            model_name="school",
            name="mailbox",
            field=models.CharField(blank=True, max_length=30, verbose_name="boîte postale"),
        ),
        migrations.AddField(
            model_name="school",
            name="address",
            field=models.CharField(blank=True, max_length=255, verbose_name="adresse"),
        ),
        migrations.AddField(
            model_name="school",
            name="city",
            field=models.CharField(blank=True, max_length=100, verbose_name="commune"),
        ),
        migrations.AddField(
            model_name="school",
            name="cog_code",
            field=models.CharField(
                blank=True, max_length=10, verbose_name="code COG de la commune"
            ),
        ),
        migrations.AddField(
            model_name="school",
            name="cedex",
            field=models.CharField(blank=True, max_length=30, verbose_name="cedex"),
        ),
        migrations.AddField(
            model_name="school",
            name="phone",
            field=phonenumber_field.modelfields.PhoneNumberField(
                blank=True, max_length=128, region=None, verbose_name="téléphone"
            ),
        ),
        migrations.AddField(
            model_name="school",
            name="borough",
            field=models.CharField(blank=True, max_length=10, verbose_name="arrondissement"),
        ),
        migrations.AddField(
            model_name="school",
            name="department",
            field=models.CharField(blank=True, max_length=50, verbose_name="département"),
        ),
        migrations.AddField(
            model_name="school",
            name="academy",
            field=models.CharField(blank=True, max_length=50, verbose_name="académie"),
        ),
        migrations.AddField(
            model_name="school",
            name="region",
            field=models.CharField(blank=True, max_length=50, verbose_name="région"),
        ),
        migrations.AddField(
            model_name="school",
            name="region_code",
            field=models.CharField(blank=True, max_length=10, verbose_name="code COG de région"),
        ),
        migrations.AddField(
            model_name="school",
            name="longitude",
            field=models.FloatField(blank=True, null=True, verbose_name="longitude"),
        ),
        migrations.AddField(
            model_name="school",
            name="latitude",
            field=models.FloatField(blank=True, null=True, verbose_name="latitude"),
        ),
        migrations.AddField(
            model_name="school",
            name="secondary",
            field=models.BooleanField(default=False, verbose_name="enseignement secondaire"),
        ),
        migrations.AddField(
            model_name="school",
            name="higher_ed",
            field=models.BooleanField(default=False, verbose_name="enseignement supérieur"),
        ),
        migrations.AddField(
            model_name="school",
            name="training_ambassador_eligible",
            field=models.BooleanField(
                default=False, verbose_name="éligible ambassadrice de formation"
            ),
        ),
        migrations.AlterField(
            model_name="school",
            name="name",
            field=models.CharField(max_length=350, verbose_name="nom de l'établissement"),
        ),
        migrations.AlterField(
            model_name="school",
            name="name_normalized",
            field=models.CharField(blank=True, editable=False, max_length=350),
        ),
        # --- the parcours FK must tolerate an unresolved school before the data moves
        migrations.AlterField(
            model_name="trainingexperience",
            name="school",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="training_experiences",
                to="techpourtoutes.school",
                verbose_name="établissement",
            ),
        ),
        migrations.AlterField(
            model_name="trainingexperience",
            name="level",
            field=models.CharField(
                blank=True, choices=LEVEL_CHOICES, max_length=20, verbose_name="niveau"
            ),
        ),
        migrations.AlterModelOptions(
            name="trainingexperience",
            options={
                "ordering": ["-start_date"],
                "verbose_name": "formation suivie",
                "verbose_name_plural": "formations suivies",
            },
        ),
        # --- the new tables
        migrations.CreateModel(
            name="Formation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="primary key for the record as UUID",
                        primary_key=True,
                        serialize=False,
                        verbose_name="id",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="date and time at which a record was created",
                        verbose_name="créé le",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="date and time at which a record was last updated",
                        verbose_name="mis à jour le",
                    ),
                ),
                (
                    "onisep_id",
                    models.CharField(max_length=20, unique=True, verbose_name="identifiant Onisep"),
                ),
                ("code_nsf", models.CharField(blank=True, max_length=50, verbose_name="code NSF")),
                (
                    "code_scolarite",
                    models.CharField(blank=True, max_length=20, verbose_name="code scolarité"),
                ),
                (
                    "type_acronym",
                    models.CharField(
                        blank=True, max_length=20, verbose_name="sigle du type de formation"
                    ),
                ),
                (
                    "type_name",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="libellé du type de formation"
                    ),
                ),
                ("name", models.CharField(max_length=255, verbose_name="libellé de la formation")),
                (
                    "acronym",
                    models.CharField(
                        blank=True, max_length=20, verbose_name="sigle de la formation"
                    ),
                ),
                (
                    "duration_in_years",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="durée en années"
                    ),
                ),
                (
                    "exit_level",
                    models.CharField(
                        blank=True,
                        choices=LEVEL_CHOICES,
                        max_length=20,
                        verbose_name="niveau de sortie",
                    ),
                ),
                (
                    "code_rncp",
                    models.CharField(blank=True, max_length=10, verbose_name="code RNCP"),
                ),
                (
                    "certification_level",
                    models.CharField(
                        blank=True, max_length=5, verbose_name="niveau de certification"
                    ),
                ),
                (
                    "certification_level_name",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        verbose_name="libellé du niveau de certification",
                    ),
                ),
            ],
            options={
                "verbose_name": "formation",
                "verbose_name_plural": "formations",
            },
        ),
        migrations.CreateModel(
            name="FormationAction",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="primary key for the record as UUID",
                        primary_key=True,
                        serialize=False,
                        verbose_name="id",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="date and time at which a record was created",
                        verbose_name="créé le",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="date and time at which a record was last updated",
                        verbose_name="mis à jour le",
                    ),
                ),
                (
                    "onisep_id",
                    models.CharField(max_length=20, unique=True, verbose_name="identifiant Onisep"),
                ),
                (
                    "formation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="actions",
                        to="techpourtoutes.formation",
                        verbose_name="formation",
                    ),
                ),
                (
                    "school",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="actions",
                        to="techpourtoutes.school",
                        verbose_name="établissement",
                    ),
                ),
            ],
            options={
                "verbose_name": "action de formation",
                "verbose_name_plural": "actions de formation",
            },
        ),
        migrations.AddField(
            model_name="formation",
            name="schools",
            field=models.ManyToManyField(
                related_name="formations",
                through="techpourtoutes.FormationAction",
                to="techpourtoutes.school",
                verbose_name="établissements",
            ),
        ),
        # --- the merge itself. Dropping the columns it makes redundant has to wait for the
        # next migration: Postgres refuses to ALTER a table that still has pending triggers
        # from the rows we just moved.
        migrations.RunPython(merge_schools, migrations.RunPython.noop),
    ]
