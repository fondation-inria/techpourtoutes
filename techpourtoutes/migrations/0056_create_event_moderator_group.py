from django.apps import apps as global_apps
from django.db import migrations

# Kept as a literal, not imported from the app: a migration must stay runnable from an empty
# database whatever the code becomes later.
EVENT_MODERATOR_GROUP_NAME = "Chargée de mission"
MODERATION_PERMISSIONS = ["view_event", "change_event"]


def create_event_moderator_group(apps, schema_editor):
    """The group a Chargée de mission belongs to: she opens an event to decide its fate, and
    nothing else — no adding, no deleting, no other model."""
    # Permissions are normally created by the `post_migrate` signal, which only fires once the
    # whole `migrate` run is over — too late to hand them to a group here. Creating them up
    # front is the documented workaround.
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config("techpourtoutes"), apps=apps, verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    event_content_type = ContentType.objects.get(app_label="techpourtoutes", model="event")
    group = Group.objects.create(name=EVENT_MODERATOR_GROUP_NAME)
    group.permissions.set(
        Permission.objects.filter(
            content_type=event_content_type, codename__in=MODERATION_PERMISSIONS
        )
    )


def delete_event_moderator_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=EVENT_MODERATOR_GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0055_alter_event_subcategory_and_more"),
        ("auth", "0001_initial"),
        ("contenttypes", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_event_moderator_group, delete_event_moderator_group),
    ]
