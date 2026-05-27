from unittest.mock import patch

import pytest
from django.db import transaction
from django.test import override_settings


@pytest.fixture
def mock_tasks():
    with (
        patch("techpourtoutes.signals.upsert_brevo_contact_task") as upsert,
        patch("techpourtoutes.signals.delete_brevo_contact_task") as delete,
    ):
        yield upsert, delete


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test")
def test_post_save_signal_dispatches_upsert_task_after_commit(valid_mentor_model_data, mock_tasks):
    upsert_task, _delete_task = mock_tasks
    from techpourtoutes.models import Mentor

    with transaction.atomic():
        mentor = Mentor(username=valid_mentor_model_data["email"], **valid_mentor_model_data)
        mentor.save()
        upsert_task.delay.assert_not_called()

    upsert_task.delay.assert_called_once_with(str(mentor.pk), "techpourtoutes.Mentor")


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test", BREVO_MENTOR_LIST_ID=42)
def test_pre_delete_signal_dispatches_delete_task_after_commit(mentor, mock_tasks):
    _upsert_task, delete_task = mock_tasks
    mentor_pk = str(mentor.pk)

    delete_task.delay.reset_mock()
    with transaction.atomic():
        mentor.delete()
        delete_task.delay.assert_not_called()

    delete_task.delay.assert_called_once_with(mentor_pk, 42)


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test")
def test_signal_skipped_when_brevo_sync_disabled(valid_mentor_model_data, mock_tasks):
    upsert_task, _ = mock_tasks
    from techpourtoutes.models import Mentor

    mentor = Mentor(
        username=valid_mentor_model_data["email"],
        brevo_sync_enabled=False,
        **valid_mentor_model_data,
    )
    mentor.save()

    upsert_task.delay.assert_not_called()


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test", BREVO_SYNC_ENABLED=False)
def test_signal_skipped_when_brevo_sync_globally_disabled(valid_mentor_model_data, mock_tasks):
    upsert_task, _ = mock_tasks
    from techpourtoutes.models import Mentor

    with transaction.atomic():
        Mentor(username=valid_mentor_model_data["email"], **valid_mentor_model_data).save()

    upsert_task.delay.assert_not_called()


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test", BREVO_SYNC_ENABLED=False)
def test_delete_signal_skipped_when_brevo_sync_globally_disabled(mentor, mock_tasks):
    _upsert_task, delete_task = mock_tasks
    delete_task.delay.reset_mock()

    with transaction.atomic():
        mentor.delete()

    delete_task.delay.assert_not_called()


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test")
def test_signal_does_not_dispatch_on_rolled_back_transaction(valid_mentor_model_data, mock_tasks):
    upsert_task, _ = mock_tasks
    from techpourtoutes.models import Mentor

    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        with transaction.atomic():
            Mentor(username=valid_mentor_model_data["email"], **valid_mentor_model_data).save()
            raise Boom

    upsert_task.delay.assert_not_called()
