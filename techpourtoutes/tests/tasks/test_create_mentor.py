from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from techpourtoutes.tasks._retry import TransientError
from techpourtoutes.tasks.create_mentor import create_mentor_task

REGISTER = "techpourtoutes.tasks.create_mentor.RegisterUserOnJobirl"

pytestmark = pytest.mark.django_db


def test_task_registers_the_pro_and_saves_her_credentials(pro):
    registered = MagicMock(failure=False, errors=[], user_id=287565, token="tpt_abc")

    with patch(REGISTER, return_value=registered) as MockRegister:
        create_mentor_task(str(pro.pk))

    assert MockRegister.call_args.kwargs["user"].pk == pro.pk
    pro.refresh_from_db()
    assert pro.jobirl_user_id == 287565
    assert pro.jobirl_user_token == "tpt_abc"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_the_catch_up_replays_nothing_the_first_pass_already_did(pro):
    """The pro was saved and notified before the task was ever enqueued."""
    from django.core import mail

    engagements = list(pro.engagements)
    registered = MagicMock(failure=False, errors=[], user_id=287565, token="tpt_abc")

    with patch(REGISTER, return_value=registered):
        create_mentor_task(str(pro.pk))

    pro.refresh_from_db()
    assert pro.engagements == engagements
    assert mail.outbox == []


def test_task_raises_runtime_error_on_permanent_failure(pro):
    failed = MagicMock(failure=True, errors=["boom"], failed_with_transient_error=False)

    with patch(REGISTER, return_value=failed):
        with pytest.raises(RuntimeError, match="boom"):
            create_mentor_task(str(pro.pk))


def test_task_raises_transient_error_on_transient_failure(pro):
    failed = MagicMock(failure=True, errors=["boom"], failed_with_transient_error=True)

    with patch(REGISTER, return_value=failed):
        with pytest.raises(TransientError, match="boom"):
            create_mentor_task(str(pro.pk))
