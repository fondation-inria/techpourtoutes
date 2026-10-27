from datetime import timedelta

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from techpourtoutes.models import Beneficiary, LegalRepresentativeAuthorization

BEFORE = [("techpourtoutes", "0065_legal_representative_authorization")]
AFTER = [("techpourtoutes", "0066_move_legal_representative_to_authorization")]


@pytest.fixture
def historical_apps(transactional_db):
    """The models as they stood when a beneficiary still carried her legal representative."""
    executor = MigrationExecutor(connection)
    executor.migrate(BEFORE)
    yield executor.loader.project_state(BEFORE).apps
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def _migrate_to_after():
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(AFTER)


@pytest.fixture
def historical_beneficiary(historical_apps):
    return historical_apps.get_model("techpourtoutes", "Beneficiary")


def _beneficiary(model, email, *, legal_representative_email="", jobirl_user_id=None, days=0):
    beneficiary = model.objects.create(
        username=email,
        email=email,
        legal_representative_name="Marie Petit" if legal_representative_email else "",
        legal_representative_email=legal_representative_email,
        jobirl_user_id=jobirl_user_id,
    )
    model.objects.filter(pk=beneficiary.pk).update(
        created_at=timezone.now() - timedelta(days=days)
    )
    return beneficiary


def _authorization_of(email):
    return LegalRepresentativeAuthorization.objects.filter(beneficiary__email=email).first()


def test_a_minor_already_on_jobirl_counts_as_signed(historical_beneficiary):
    _beneficiary(
        historical_beneficiary,
        "jade@example.com",
        legal_representative_email="marie@example.com",
        jobirl_user_id=42,
        days=60,
    )

    _migrate_to_after()

    authorization = _authorization_of("jade@example.com")
    assert authorization.status == LegalRepresentativeAuthorization.Status.SIGNED
    assert authorization.legal_representative_name == "Marie Petit"
    assert authorization.legal_representative_email == "marie@example.com"


def test_a_recent_request_stays_pending(historical_beneficiary):
    _beneficiary(
        historical_beneficiary,
        "lou@example.com",
        legal_representative_email="marie@example.com",
        days=20,
    )

    _migrate_to_after()

    authorization = _authorization_of("lou@example.com")
    assert authorization.status == LegalRepresentativeAuthorization.Status.PENDING


def test_a_request_older_than_three_weeks_is_dropped(historical_beneficiary):
    _beneficiary(
        historical_beneficiary,
        "ines@example.com",
        legal_representative_email="marie@example.com",
        days=22,
    )

    _migrate_to_after()

    assert _authorization_of("ines@example.com") is None
    assert Beneficiary.objects.filter(email="ines@example.com").exists()


def test_an_adult_gets_no_authorization(historical_beneficiary):
    _beneficiary(historical_beneficiary, "lea@example.com", jobirl_user_id=7)

    _migrate_to_after()

    assert _authorization_of("lea@example.com") is None
