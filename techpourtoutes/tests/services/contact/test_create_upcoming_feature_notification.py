from unittest.mock import patch

import pytest

from techpourtoutes.services.contact.create_upcoming_feature_notification import (
    CreateUpcomingFeatureNotification,
)

UPSERT = "techpourtoutes.services.contact.create_upcoming_feature_notification.UpsertBrevoContact"


@pytest.mark.parametrize("list_id", [18, 21])
def test_create_upcoming_feature_notification_upserts_the_contact_into_the_given_list(list_id):
    with patch(UPSERT) as upsert:
        upsert.return_value.failure = False
        result = CreateUpcomingFeatureNotification(email="hedy@example.com", list_id=list_id)

    assert result.success
    assert upsert.call_args.kwargs["list_id"] == list_id


def test_create_upcoming_feature_notification_skips_a_list_left_unset():
    with patch(UPSERT) as upsert:
        result = CreateUpcomingFeatureNotification(email="hedy@example.com", list_id=0)

    assert result.success
    upsert.assert_not_called()
