from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, pre_delete

from techpourtoutes.services.brevo_api.mappings import brevo_list_id_for
from techpourtoutes.tasks.delete_brevo_contact import delete_brevo_contact_task
from techpourtoutes.tasks.upsert_brevo_contact import upsert_brevo_contact_task


def _on_user_saved(sender, instance, **kwargs):
    if not settings.BREVO_SYNC_ENABLED or not instance.brevo_sync_enabled:
        return
    pk = str(instance.pk)
    model_label = sender._meta.label
    transaction.on_commit(lambda: upsert_brevo_contact_task.delay(pk, model_label))


def _on_user_deleted(sender, instance, **kwargs):
    if not settings.BREVO_SYNC_ENABLED or not instance.brevo_sync_enabled:
        return
    list_id = brevo_list_id_for(instance)
    if list_id is None:
        return
    pk = str(instance.pk)
    transaction.on_commit(lambda: delete_brevo_contact_task.delay(pk, list_id))


def connect_brevo_sync(model_cls):
    """Connect post_save (upsert) and pre_delete (delete) Brevo sync handlers for the given model.

    Call this once from each user-subclass model file (e.g. at the bottom of pro.py).
    """
    post_save.connect(_on_user_saved, sender=model_cls, weak=False)
    pre_delete.connect(_on_user_deleted, sender=model_cls, weak=False)
