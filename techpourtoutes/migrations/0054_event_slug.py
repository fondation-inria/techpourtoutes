from django.db import migrations, models
from django.utils.text import slugify


def write_slugs(apps, schema_editor):
    """Existing events have none: the column is filled before it turns unique."""
    Event = apps.get_model("techpourtoutes", "Event")
    taken = set()
    for event in Event.objects.all():
        base = slugify(event.title)[:240] or "evenement"
        slug, rank = base, 1
        while slug in taken:
            rank += 1
            slug = f"{base}-{rank}"
        taken.add(slug)
        Event.objects.filter(pk=event.pk).update(slug=slug)


class Migration(migrations.Migration):

    dependencies = [
        ("techpourtoutes", "0053_event_poi_name_historicalevent_poi_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="slug",
            field=models.SlugField(
                db_index=False, default="", max_length=255, verbose_name="slug"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="historicalevent",
            name="slug",
            field=models.SlugField(
                db_index=False, default="", max_length=255, verbose_name="slug"
            ),
            preserve_default=False,
        ),
        migrations.RunPython(write_slugs, migrations.RunPython.noop, elidable=True),
        migrations.AlterField(
            model_name="event",
            name="slug",
            field=models.SlugField(max_length=255, unique=True, verbose_name="slug"),
        ),
        migrations.AlterField(
            model_name="historicalevent",
            name="slug",
            field=models.SlugField(db_index=True, max_length=255, verbose_name="slug"),
        ),
    ]
