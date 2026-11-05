from unittest.mock import patch

import pytest
from billiard.exceptions import WorkerLostError
from celery.signals import task_failure
from django.core.management.sql import emit_post_migrate_signal
from django.db import connection, transaction
from django.test import override_settings

from techpourtoutes.models import LegalRepresentativeAuthorization, Pro
from techpourtoutes.signals import legal_representative_authorization_signed
from techpourtoutes.tasks import import_apec_job_postings_task

APEC_TASK = "techpourtoutes.tasks.import_apec_job_postings.import_apec_job_postings_task"


@pytest.fixture
def mock_tasks():
    with (
        patch("techpourtoutes.signals.upsert_brevo_contact_task") as upsert,
        patch("techpourtoutes.signals.delete_brevo_contact_task") as delete,
    ):
        yield upsert, delete


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test")
def test_post_save_signal_dispatches_upsert_task_after_commit(valid_pro_model_data, mock_tasks):
    upsert_task, _delete_task = mock_tasks

    with transaction.atomic():
        pro = Pro(
            username=valid_pro_model_data["email"],
            brevo_sync_enabled=True,
            **valid_pro_model_data,
        )
        pro.save()
        upsert_task.delay.assert_not_called()

    upsert_task.delay.assert_called_once_with(
        instance_pk=str(pro.pk), model_label="techpourtoutes.Pro"
    )


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test", BREVO_PRO_LIST_ID=42)
def test_pre_delete_signal_dispatches_delete_task_after_commit(pro, mock_tasks):
    _upsert_task, delete_task = mock_tasks
    pro_pk = str(pro.pk)

    delete_task.delay.reset_mock()
    with transaction.atomic():
        pro.delete()
        delete_task.delay.assert_not_called()

    delete_task.delay.assert_called_once_with(ext_id=pro_pk, list_id=42)


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test")
def test_signal_skipped_when_brevo_sync_disabled(valid_pro_model_data, mock_tasks):
    upsert_task, _ = mock_tasks

    pro = Pro(
        username=valid_pro_model_data["email"],
        brevo_sync_enabled=False,
        **valid_pro_model_data,
    )
    pro.save()

    upsert_task.delay.assert_not_called()


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test", BREVO_SYNC_ENABLED=False)
def test_signal_skipped_when_brevo_sync_globally_disabled(valid_pro_model_data, mock_tasks):
    upsert_task, _ = mock_tasks

    with transaction.atomic():
        Pro(username=valid_pro_model_data["email"], **valid_pro_model_data).save()

    upsert_task.delay.assert_not_called()


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test", BREVO_SYNC_ENABLED=False)
def test_delete_signal_skipped_when_brevo_sync_globally_disabled(pro, mock_tasks):
    _upsert_task, delete_task = mock_tasks
    delete_task.delay.reset_mock()

    with transaction.atomic():
        pro.delete()

    delete_task.delay.assert_not_called()


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test", BREVO_PRO_LIST_ID=42)
def test_opt_out_transition_dispatches_delete(pro, mock_tasks):
    upsert_task, delete_task = mock_tasks

    reloaded = Pro.objects.get(pk=pro.pk)
    upsert_task.delay.reset_mock()
    delete_task.delay.reset_mock()

    with transaction.atomic():
        reloaded.brevo_sync_enabled = False
        reloaded.save()

    delete_task.delay.assert_called_once_with(ext_id=str(pro.pk), list_id=42)
    upsert_task.delay.assert_not_called()


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test", BREVO_PRO_LIST_ID=42)
def test_opt_out_delete_dispatched_only_once_across_saves(pro, mock_tasks):
    _upsert_task, delete_task = mock_tasks

    reloaded = Pro.objects.get(pk=pro.pk)
    delete_task.delay.reset_mock()

    with transaction.atomic():
        reloaded.brevo_sync_enabled = False
        reloaded.save()
        reloaded.save()

    delete_task.delay.assert_called_once_with(ext_id=str(pro.pk), list_id=42)


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test", BREVO_PRO_LIST_ID=42)
def test_new_unsynced_pro_does_not_dispatch_delete(valid_pro_model_data, mock_tasks):
    upsert_task, delete_task = mock_tasks

    with transaction.atomic():
        Pro(
            username=valid_pro_model_data["email"],
            brevo_sync_enabled=False,
            **valid_pro_model_data,
        ).save()

    delete_task.delay.assert_not_called()
    upsert_task.delay.assert_not_called()


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test")
def test_signal_does_not_dispatch_on_rolled_back_transaction(valid_pro_model_data, mock_tasks):
    upsert_task, _ = mock_tasks

    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        with transaction.atomic():
            Pro(username=valid_pro_model_data["email"], **valid_pro_model_data).save()
            raise Boom

    upsert_task.delay.assert_not_called()


@pytest.mark.django_db
def test_joining_a_group_opens_the_admin_door(pro, event_moderator_group):
    """A group carries permissions, and they only apply behind the door `is_staff` opens:
    handing out a role is the whole gesture, nothing else to remember to tick."""
    pro.groups.add(event_moderator_group)

    pro.refresh_from_db()
    assert pro.is_staff


@pytest.mark.django_db
def test_leaving_every_group_closes_the_admin_door(pro, event_moderator_group):
    pro.groups.add(event_moderator_group)
    pro.groups.remove(event_moderator_group)

    pro.refresh_from_db()
    assert not pro.is_staff


@pytest.mark.django_db
def test_clearing_the_groups_closes_the_admin_door(pro, event_moderator_group):
    pro.groups.add(event_moderator_group)
    pro.groups.clear()

    pro.refresh_from_db()
    assert not pro.is_staff


@pytest.mark.django_db
def test_a_signed_legal_representative_authorization_registers_the_mentoree(authorization):
    with patch("techpourtoutes.signals.create_mentoree_task") as create_mentoree:
        legal_representative_authorization_signed.send(
            sender=LegalRepresentativeAuthorization, authorization=authorization
        )

    create_mentoree.delay.assert_called_once_with(beneficiary_pk=str(authorization.beneficiary.pk))


@pytest.mark.django_db
def test_the_update_date_triggers_are_installed_after_every_migration():
    """A new model gets its trigger without a migration of its own."""
    with patch("techpourtoutes.signals.install_updated_at_triggers") as install:
        emit_post_migrate_signal(verbosity=0, interactive=False, db="default")

    install.assert_called_once_with(connection)


def test_a_task_whose_worker_process_died_is_reported_to_sentry_by_its_name():
    """Killed mid-task, the process cannot report anything: the worker's main process does."""
    with patch("techpourtoutes.signals.sentry_sdk.capture_message") as capture:
        task_failure.send(
            sender=import_apec_job_postings_task,
            task_id="261f7130",
            exception=WorkerLostError("Worker exited prematurely: signal 9 (SIGKILL) Job: 2."),
        )

    capture.assert_called_once_with(
        f"{APEC_TASK} did not complete: Worker exited prematurely: signal 9 (SIGKILL) Job: 2.",
        level="error",
        fingerprint=["celery-worker-lost", APEC_TASK],
        tags={"celery_task": APEC_TASK},
    )


def test_a_task_that_raised_is_left_to_the_celery_integration():
    with patch("techpourtoutes.signals.sentry_sdk.capture_message") as capture:
        task_failure.send(
            sender=import_apec_job_postings_task, task_id="261f7130", exception=RuntimeError()
        )

    capture.assert_not_called()
