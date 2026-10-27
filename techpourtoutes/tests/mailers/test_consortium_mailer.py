import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.forms.pro_inscription import OTHER
from techpourtoutes.mailers import ConsortiumMailer
from techpourtoutes.models import Formation, Pro, TrainingExperience


@pytest.mark.django_db
@override_settings(
    COALITION_INTERNSHIPS_RECIPIENTS=["internships@example.com"],
    COALITION_WORK_AMBASSADOR_RECIPIENTS=["ambassador@example.com"],
    COALITION_TRAINING_AMBASSADOR_RECIPIENTS=["training@example.com"],
    COALITION_SPONSOR_RECIPIENTS=["sponsor@example.com"],
)
@pytest.mark.parametrize(
    "engagement,recipient",
    [
        (Pro.Engagement.INTERNSHIPS, "internships@example.com"),
        (Pro.Engagement.WORK_AMBASSADOR, "ambassador@example.com"),
        (Pro.Engagement.SPONSOR, "sponsor@example.com"),
    ],
)
def test_pro_signed_up_routes_to_engagement_recipient(pro, engagement, recipient):
    ConsortiumMailer.pro_signed_up(pro=pro, engagement=engagement)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [recipient]
    assert str(Pro.Engagement(engagement).label) in message.subject


structure_type_recipients = override_settings(
    COALITION_ASSOCIATION_RECIPIENTS=["association@example.com"],
    COALITION_TRAINING_AMBASSADOR_RECIPIENTS=["training@example.com"],
    COALITION_SCHOOL_RECIPIENTS=["school@example.com"],
    COALITION_WORK_AMBASSADOR_RECIPIENTS=["ambassador@example.com"],
    COALITION_PUBLIC_INSTITUTION_RECIPIENTS=["public@example.com"],
)

RECIPIENT_BY_STRUCTURE_TYPE = [
    (Pro.StructureType.ASSOCIATION, "association@example.com"),
    (Pro.StructureType.HIGHER_ED, "training@example.com"),
    (Pro.StructureType.SCHOOL, "school@example.com"),
    (Pro.StructureType.COMPANY, "ambassador@example.com"),
    (Pro.StructureType.PUBLIC_INSTITUTION, "public@example.com"),
    (Pro.StructureType.RETIRED, "ambassador@example.com"),
    (Pro.StructureType.JOBLESS, "ambassador@example.com"),
    # Never said: the coalition's general address rather than nobody.
    ("", "agir@techpourtoutes.io"),
]


@pytest.mark.django_db
@structure_type_recipients
@pytest.mark.parametrize("engagement", [Pro.Engagement.MOBILIZE_STRUCTURE, OTHER])
@pytest.mark.parametrize("structure_type,recipient", RECIPIENT_BY_STRUCTURE_TYPE)
def test_pro_signed_up_routes_a_structure_engagement_to_her_structure_type_recipient(
    pro, engagement, structure_type, recipient
):
    pro.structure_type = structure_type

    ConsortiumMailer.pro_signed_up(pro=pro, engagement=engagement)

    assert mail.outbox[0].to == [recipient]


@pytest.mark.django_db
@override_settings(
    COALITION_WORK_AMBASSADOR_RECIPIENTS=["ambassador@example.com"],
)
def test_pro_signed_up_relays_the_message_of_another_engagement(pro):
    pro.structure_type = Pro.StructureType.COMPANY

    ConsortiumMailer.pro_signed_up(pro=pro, engagement=OTHER, message="Je veux aider autrement.")

    message = mail.outbox[0]
    assert message.to == ["ambassador@example.com"]
    assert "s'engager autrement" in message.subject
    assert "Je veux aider autrement." in message.body
    assert "Je veux aider autrement." in message.alternatives[0][0]
    assert pro.email in message.body


@pytest.mark.django_db
@override_settings(
    COALITION_SPONSOR_RECIPIENTS=["sponsor@example.com"],
)
def test_pro_signed_up_without_a_message_announces_none(pro):
    ConsortiumMailer.pro_signed_up(pro=pro, engagement=Pro.Engagement.SPONSOR)

    message = mail.outbox[0]
    assert "Voici son message" not in message.body
    assert "Voici son message" not in message.alternatives[0][0]


@pytest.mark.django_db
@override_settings(
    COALITION_SPONSOR_RECIPIENTS=["sponsor@example.com"],
)
def test_pro_signed_up_without_a_structure_names_none(pro):
    pro.structure_name = ""

    ConsortiumMailer.pro_signed_up(pro=pro, engagement=Pro.Engagement.SPONSOR)

    message = mail.outbox[0]
    assert "de la structure" not in message.body
    assert "de la structure" not in message.alternatives[0][0]


@pytest.mark.django_db
@override_settings(
    COALITION_TRAINING_AMBASSADOR_RECIPIENTS=["training@example.com"],
)
def test_training_ambassador_signed_up_includes_experience_in_body(pro, higher_ed_school):
    formation = Formation(onisep_id="9701", name="Master IA")
    formation.save()
    experience = TrainingExperience.objects.create(
        user=pro, school=higher_ed_school, formation=formation
    )
    ConsortiumMailer.training_ambassador_signed_up(pro=pro, training_experience=experience)

    message = mail.outbox[0]
    assert message.to == ["training@example.com"]
    assert "Master IA" in message.body
    assert higher_ed_school.name in message.body


@pytest.mark.django_db
@override_settings(
    COALITION_WORK_AMBASSADOR_RECIPIENTS=["ambassador@example.com"],
)
def test_pro_signed_up_includes_pro_details_in_body(pro):
    ConsortiumMailer.pro_signed_up(pro=pro, engagement=Pro.Engagement.WORK_AMBASSADOR)

    body = mail.outbox[0].body
    assert pro.first_name in body
    assert pro.last_name in body
    assert pro.email in body


@pytest.mark.django_db
@structure_type_recipients
def test_event_submitted_notifies_the_moderation_team(event):
    event.created_by.structure_type = Pro.StructureType.ASSOCIATION

    ConsortiumMailer.event_submitted(event=event)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["association@example.com"]
    assert event.title in message.body
    assert event.created_by.email in message.body
    assert message.tags == ["interne", "coalition", "nouvel événement"]


@pytest.mark.django_db
@structure_type_recipients
@pytest.mark.parametrize("structure_type,recipient", RECIPIENT_BY_STRUCTURE_TYPE)
def test_event_submitted_routes_to_the_team_of_the_authors_structure_type(
    event, structure_type, recipient
):
    event.created_by.structure_type = structure_type

    ConsortiumMailer.event_submitted(event=event)

    assert mail.outbox[0].to == [recipient]


@pytest.mark.django_db
@override_settings(SITE_URL="https://example.test")
def test_event_submitted_links_to_the_event_in_the_admin_through_the_user_login(event):
    """Moderators sign in through the user login, not the admin's: the link goes through it."""
    event.created_by.structure_type = Pro.StructureType.ASSOCIATION

    ConsortiumMailer.event_submitted(event=event)

    expected_url = (
        "https://example.test/se-connecter/"
        f"?next=%2Fadmin%2Ftechpourtoutes%2Fevent%2F{event.pk}%2Fchange%2F"
    )
    message = mail.outbox[0]
    assert expected_url in message.body
    assert expected_url in message.alternatives[0][0]


@pytest.mark.django_db
@structure_type_recipients
@pytest.mark.parametrize("structure_type,recipient", RECIPIENT_BY_STRUCTURE_TYPE)
def test_event_updated_routes_to_the_team_of_the_authors_structure_type(
    event, structure_type, recipient
):
    event.created_by.structure_type = structure_type

    ConsortiumMailer.event_updated(event=event)

    assert mail.outbox[0].to == [recipient]


@pytest.mark.django_db
@override_settings(SITE_URL="https://example.test")
def test_event_updated_links_to_the_event_in_the_admin_through_the_user_login(event):
    event.created_by.structure_type = Pro.StructureType.ASSOCIATION

    ConsortiumMailer.event_updated(event=event)

    expected_url = (
        "https://example.test/se-connecter/"
        f"?next=%2Fadmin%2Ftechpourtoutes%2Fevent%2F{event.pk}%2Fchange%2F"
    )
    message = mail.outbox[0]
    assert expected_url in message.body
    assert expected_url in message.alternatives[0][0]
