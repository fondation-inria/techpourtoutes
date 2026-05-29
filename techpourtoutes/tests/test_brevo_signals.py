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
def test_post_save_signal_dispatches_upsert_task_after_commit(valid_pro_model_data, mock_tasks):
    upsert_task, _delete_task = mock_tasks
    from techpourtoutes.models import Pro

    with transaction.atomic():
        pro = Pro(username=valid_pro_model_data["email"], **valid_pro_model_data)
        pro.save()
        upsert_task.delay.assert_not_called()

    upsert_task.delay.assert_called_once_with(str(pro.pk), "techpourtoutes.Pro")


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test", BREVO_PRO_LIST_ID=42)
def test_pre_delete_signal_dispatches_delete_task_after_commit(pro, mock_tasks):
    _upsert_task, delete_task = mock_tasks
    pro_pk = str(pro.pk)

    delete_task.delay.reset_mock()
    with transaction.atomic():
        pro.delete()
        delete_task.delay.assert_not_called()

    delete_task.delay.assert_called_once_with(pro_pk, 42)


@pytest.mark.django_db(transaction=True)
@override_settings(BREVO_API_KEY="test")
def test_signal_skipped_when_brevo_sync_disabled(valid_pro_model_data, mock_tasks):
    upsert_task, _ = mock_tasks
    from techpourtoutes.models import Pro

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
    from techpourtoutes.models import Pro

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
@override_settings(BREVO_API_KEY="test")
def test_signal_does_not_dispatch_on_rolled_back_transaction(valid_pro_model_data, mock_tasks):
    upsert_task, _ = mock_tasks
    from techpourtoutes.models import Pro

    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        with transaction.atomic():
            Pro(username=valid_pro_model_data["email"], **valid_pro_model_data).save()
            raise Boom

    upsert_task.delay.assert_not_called()
