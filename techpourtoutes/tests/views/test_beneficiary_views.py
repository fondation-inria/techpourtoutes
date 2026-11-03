import re
from datetime import time, timedelta
from unittest.mock import patch

import pytest
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from waffle.testutils import override_switch

from techpourtoutes.models import Event, JobPosting, MakeuseProject, Pro, SavedEvent, User
from techpourtoutes.utils.territories import REGIONS

from ..models.test_event import build_event
from ..models.test_makeuse_project import build_makeuse_project

NEW_UPCOMING_FEATURE_NOTIFICATION_URL = "/bientot-disponible/"
CREATE_UPCOMING_FEATURE_NOTIFICATION_URL = "/bientot-disponible/inscription/"


@pytest.mark.django_db
def test_new_upcoming_feature_notification_get_returns_200(client):
    assert client.get(NEW_UPCOMING_FEATURE_NOTIFICATION_URL).status_code == 200


@pytest.mark.django_db
@override_settings(BREVO_SYNC_ENABLED=True)
def test_create_upcoming_feature_notification_valid_pushes_brevo_contact_and_redirects(client):
    with patch(
        "techpourtoutes.views.beneficiary_views.create_upcoming_feature_notification_task"
    ) as mock_task:
        response = client.post(
            CREATE_UPCOMING_FEATURE_NOTIFICATION_URL, data={"email": "hedy@example.com"}
        )

    assert response.status_code == 302
    assert response.url == NEW_UPCOMING_FEATURE_NOTIFICATION_URL
    mock_task.delay.assert_called_once_with(email="hedy@example.com")


@pytest.mark.django_db
@override_settings(BREVO_SYNC_ENABLED=False)
def test_create_upcoming_feature_notification_skips_task_when_sync_disabled(client):
    with patch(
        "techpourtoutes.views.beneficiary_views.create_upcoming_feature_notification_task"
    ) as mock_task:
        response = client.post(
            CREATE_UPCOMING_FEATURE_NOTIFICATION_URL, data={"email": "hedy@example.com"}
        )

    assert response.status_code == 302
    mock_task.delay.assert_not_called()


@pytest.mark.django_db
def test_create_upcoming_feature_notification_invalid_rerenders_with_errors(client):
    response = client.post(
        CREATE_UPCOMING_FEATURE_NOTIFICATION_URL, data={"email": "not-an-email"}
    )
    assert response.status_code == 200
    assert response.context["form"].errors
    messages = list(response.context["messages"])
    assert len(messages) > 0


NEW_MENTOREE_URL = "/trouver-une-mentore/"


@pytest.mark.django_db
def test_new_mentoree_cta_for_anonymous_user(client):
    response = client.get(NEW_MENTOREE_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == "/inscription/new/?wants_mentor=1"
    assert response.context["cta_label"] == "S'inscrire au mentorat"
    assert response.context["cta_disabled"] is False


@pytest.mark.django_db
def test_new_mentoree_cta_for_connected_unregistered_beneficiary(client, beneficiary):
    client.force_login(beneficiary)

    response = client.get(NEW_MENTOREE_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == "/devenir-mentoree/"
    assert response.context["cta_label"] == "S'inscrire au mentorat"
    assert response.context["cta_disabled"] is False


@pytest.mark.django_db
def test_new_mentoree_cta_for_connected_registered_beneficiary(client, beneficiary):
    beneficiary.jobirl_user_id = 42
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.get(NEW_MENTOREE_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == reverse("login_to_jobirl")
    assert response.context["cta_label"] == "Rejoindre mon espace mentorat"
    assert response.context["cta_disabled"] is False


@pytest.mark.django_db
def test_new_mentoree_cta_disabled_for_registration_pending_jobirl_account(
    client, beneficiary, authorization
):
    client.force_login(beneficiary)

    response = client.get(NEW_MENTOREE_URL)

    assert response.status_code == 200
    assert response.context["cta_label"] == "Rejoindre mon espace mentorat"
    assert response.context["cta_disabled"] is True


@pytest.mark.django_db
def test_new_mentoree_cta_for_connected_non_beneficiary_points_to_mentoring_funnel(client, pro):
    client.force_login(pro)

    response = client.get(NEW_MENTOREE_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == "/devenir-mentoree/"
    assert response.context["cta_label"] == "S'inscrire au mentorat"
    assert response.context["cta_disabled"] is False


NEW_TRAINING_AMBASSADOR_BENEFICIARY_URL = "/echanger-avec-une-etudiante/"


@pytest.mark.django_db
def test_new_training_ambassador_beneficiary_cta_for_anonymous_user(client):
    response = client.get(NEW_TRAINING_AMBASSADOR_BENEFICIARY_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == "/inscription/new/?wants_training_ambassador=1"
    assert response.context["cta_label"] == "Rejoindre le club"


@pytest.mark.django_db
def test_new_training_ambassador_beneficiary_cta_for_beneficiary_points_to_the_request(
    client, beneficiary
):
    client.force_login(beneficiary)

    response = client.get(NEW_TRAINING_AMBASSADOR_BENEFICIARY_URL)

    assert response.context["cta_href"] == reverse("new_training_ambassador_request")


@pytest.mark.django_db
def test_new_training_ambassador_beneficiary_cta_once_requested_points_to_account(
    client, beneficiary
):
    beneficiary.has_requested_training_ambassador = True
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.get(NEW_TRAINING_AMBASSADOR_BENEFICIARY_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == reverse("show_account")


@pytest.mark.django_db
def test_new_training_ambassador_beneficiary_no_cta_for_pro(client, pro):
    client.force_login(pro)

    response = client.get(NEW_TRAINING_AMBASSADOR_BENEFICIARY_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] is None


INDEX_JOB_POSTINGS_URL = "/stages-alternances-emplois/"


def save_job_posting(title, category, **overrides):
    JobPosting(
        **{
            "source": JobPosting.Source.APEC,
            "external_id": title,
            "title": title,
            "company_name": "Numeum",
            "description": "Une offre",
            "city": "Amiens",
            "domains": [JobPosting.Domain.DEVELOPPEMENT],
            "category": category,
            "published_at": timezone.now(),
            "url": "https://www.apec.fr/offre",
            **overrides,
        }
    ).save()


@pytest.fixture
def job_postings():
    save_job_posting("Stage de fin d'études", JobPosting.Category.HIGHER_ED_INTERNSHIP)
    save_job_posting("Alternance en développement", JobPosting.Category.APPRENTICESHIP)


@pytest.mark.django_db
@override_switch("internships", active=False)
def test_index_job_postings_not_found_when_switch_inactive(client):
    assert client.get(INDEX_JOB_POSTINGS_URL).status_code == 404


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_lists_the_requested_category_only(client, job_postings):
    response = client.get(INDEX_JOB_POSTINGS_URL, {"category": "apprenticeship"})

    assert b"Alternance en d" in response.content
    assert b"Stage de fin" not in response.content


@pytest.mark.django_db
@pytest.mark.parametrize("query", [{}, {"category": "inconnue"}])
@override_switch("internships", active=True)
def test_index_job_postings_defaults_to_higher_ed_internships(client, job_postings, query):
    response = client.get(INDEX_JOB_POSTINGS_URL, query)

    assert b"Stage de fin" in response.content
    assert b"Alternance en d" not in response.content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_shows_every_domain_of_a_posting(client):
    save_job_posting(
        "Stage",
        JobPosting.Category.HIGHER_ED_INTERNSHIP,
        domains=[JobPosting.Domain.MATHEMATIQUES, JobPosting.Domain.SYSTEME_RESEAUX_DONNEES],
    )

    html = client.get(INDEX_JOB_POSTINGS_URL).content.decode()

    for label in ["Mathématiques", "Système, réseaux, données"]:
        assert re.search(rf"#job-domain.*?<span>\s*{label}\s*</span>", html, re.DOTALL)


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_lists_the_latest_update_or_publication_first(client):
    now = timezone.now()
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    save_job_posting("Publiée il y a 5 jours", category, published_at=now - timedelta(days=5))
    save_job_posting(
        "Mise à jour aujourd'hui",
        category,
        published_at=now - timedelta(days=10),
        source_updated_at=now,
    )
    save_job_posting("Publiée hier", category, published_at=now - timedelta(days=1))

    content = client.get(INDEX_JOB_POSTINGS_URL).content.decode()

    assert (
        content.index("Mise à jour aujourd")
        < content.index("Publiée hier")
        < content.index("Publiée il y a 5 jours")
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, active_href",
    [
        ({}, INDEX_JOB_POSTINGS_URL),
        ({"category": "apprenticeship"}, f"{INDEX_JOB_POSTINGS_URL}?category=apprenticeship"),
        (
            {"category": "apprenticeship", "page": 2},
            f"{INDEX_JOB_POSTINGS_URL}?category=apprenticeship",
        ),
    ],
)
@override_switch("internships", active=True)
def test_index_job_postings_highlights_the_tab_of_the_category(client, query, active_href):
    html = client.get(INDEX_JOB_POSTINGS_URL, query).content.decode()

    assert re.findall(r'<a href="([^"]*)" role="tab"\s+class="[^"]*tab-active', html) == [
        active_href
    ]


def listed_titles(response):
    return {job_posting.title for job_posting in response.context["job_postings"]}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, expected",
    [
        ({"domain": "mathematiques"}, {"Maths", "Maths et réseaux"}),
        ({"domain": ["mathematiques", "electronique"]}, {"Maths", "Maths et réseaux", "Électro"}),
        ({"domain": "inconnu"}, {"Maths", "Maths et réseaux", "Électro"}),
        ({}, {"Maths", "Maths et réseaux", "Électro"}),
    ],
)
@override_switch("internships", active=True)
def test_index_job_postings_keeps_the_postings_of_any_ticked_domain(client, query, expected):
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    save_job_posting("Maths", category, domains=[JobPosting.Domain.MATHEMATIQUES])
    save_job_posting(
        "Maths et réseaux",
        category,
        domains=[JobPosting.Domain.MATHEMATIQUES, JobPosting.Domain.SYSTEME_RESEAUX_DONNEES],
    )
    save_job_posting("Électro", category, domains=[JobPosting.Domain.ELECTRONIQUE])

    assert listed_titles(client.get(INDEX_JOB_POSTINGS_URL, query)) == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, expected",
    [
        ({"contract_type": "cdi"}, {"CDI"}),
        ({"contract_type": ["cdi", "interim"]}, {"CDI", "Intérim"}),
        ({"contract_type": "apprenticeship"}, {"CDD", "CDI", "Intérim"}),
        ({}, {"CDD", "CDI", "Intérim"}),
    ],
)
@override_switch("internships", active=True)
def test_index_job_postings_keeps_the_postings_of_any_ticked_contract_type(
    client, query, expected
):
    for title, contract_type in [
        ("CDD", JobPosting.ContractType.CDD),
        ("CDI", JobPosting.ContractType.CDI),
        ("Intérim", JobPosting.ContractType.INTERIM),
    ]:
        save_job_posting(title, JobPosting.Category.FIRST_JOB, contract_type=contract_type)

    response = client.get(INDEX_JOB_POSTINGS_URL, {"category": "first_job", **query})

    assert listed_titles(response) == expected


EVERY_PLACE = {
    "Brest",
    "Quimper",
    "Ajaccio",
    "Porto-Vecchio",
    "Bastia",
    "Saint-Denis",
    "Saint-Pierre",
    "Londres",
}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, expected",
    [
        ({"department": "29"}, {"Brest", "Quimper"}),
        (
            {"department": ["2A", "974"]},
            {"Ajaccio", "Porto-Vecchio", "Saint-Denis", "Saint-Pierre"},
        ),
        ({"department": "2B"}, {"Bastia"}),
        ({"department": "99"}, {"Londres"}),
        ({"department": "97"}, EVERY_PLACE),
        ({}, EVERY_PLACE),
    ],
)
@override_switch("internships", active=True)
def test_index_job_postings_keeps_the_postings_of_any_ticked_department(client, query, expected):
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    for title, cog_code in [
        ("Brest", "29019"),
        ("Ajaccio", "2A004"),
        ("Saint-Denis", "97411"),
        ("Londres", "99132"),
    ]:
        save_job_posting(title, category, cog_code=cog_code)
    for title, postal_code in [
        ("Quimper", "29000"),
        ("Porto-Vecchio", "20137"),
        ("Bastia", "20200"),
        ("Saint-Pierre", "97410"),
    ]:
        save_job_posting(title, category, postal_code=postal_code)

    assert listed_titles(client.get(INDEX_JOB_POSTINGS_URL, query)) == expected


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_offers_every_domain(client):
    html = client.get(INDEX_JOB_POSTINGS_URL).content.decode()

    for domain in JobPosting.Domain:
        assert f'value="{domain.value}"' in html
        assert str(domain.label) in html


@pytest.mark.django_db
@pytest.mark.parametrize(
    "category, offered",
    [
        ("first_job", ["cdd", "cdi", "interim"]),
        ("apprenticeship", ["apprenticeship", "professionalization"]),
        ("higher_ed_internship", []),
        ("seconde_internship", []),
        ("troisieme_internship", []),
    ],
)
@override_switch("internships", active=True)
def test_index_job_postings_offers_the_contract_types_of_the_category(client, category, offered):
    html = client.get(INDEX_JOB_POSTINGS_URL, {"category": category}).content.decode()

    assert re.findall(r'name="contract_type"\s+value="([^"]*)"', html) == offered
    assert ("Type de contrat" in html) == bool(offered)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "category, offered",
    [
        ("higher_ed_internship", True),
        ("apprenticeship", True),
        ("first_job", True),
        ("seconde_internship", False),
        ("troisieme_internship", False),
    ],
)
@override_switch("internships", active=True)
def test_index_job_postings_offers_the_duration_filter_but_to_pupils(client, category, offered):
    html = client.get(INDEX_JOB_POSTINGS_URL, {"category": category}).content.decode()

    assert ('id="job_posting_duration"' in html) == offered


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_offers_every_region_and_department(client):
    html = client.get(INDEX_JOB_POSTINGS_URL).content.decode()

    for region in REGIONS:
        assert region.name in html
        for department in region.departments:
            assert re.search(rf'name="department"\s+value="{department.code}"', html)


@pytest.fixture
def twenty_one_apprenticeships():
    for index in range(21):
        save_job_posting(f"Alternance {index:02d}", JobPosting.Category.APPRENTICESHIP)


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_shows_twenty_postings_and_a_link_to_the_next_page_of_the_category(
    client, twenty_one_apprenticeships
):
    response = client.get(INDEX_JOB_POSTINGS_URL, {"category": "apprenticeship"})

    assert len(response.context["job_postings"].object_list) == 20
    assert b'href="?category=apprenticeship&page=2"' in response.content
    assert "21&nbsp;offres" in response.content.decode()


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_keeps_the_filters_in_the_link_to_the_next_page(
    client, twenty_one_apprenticeships
):
    response = client.get(
        INDEX_JOB_POSTINGS_URL,
        {"category": "apprenticeship", "domain": "developpement", "page": "1"},
    )

    assert b'href="?category=apprenticeship&amp;domain=developpement&page=2"' in response.content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_ticks_the_filters_of_the_query(client):
    html = client.get(
        INDEX_JOB_POSTINGS_URL, {"domain": "mathematiques", "department": "29"}
    ).content.decode()

    assert re.findall(r'value="([^"]*)"\s+checked', html) == ["29", "mathematiques"]
    assert 'name="region"' not in html


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_ticks_the_contract_types_of_the_query(client):
    html = client.get(
        INDEX_JOB_POSTINGS_URL, {"category": "first_job", "contract_type": "cdi"}
    ).content.decode()

    assert re.findall(r'value="([^"]*)"\s+checked', html) == ["cdi"]


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_serves_the_page_asked_for(client, twenty_one_apprenticeships):
    response = client.get(INDEX_JOB_POSTINGS_URL, {"category": "apprenticeship", "page": 2})

    assert response.context["job_postings"].number == 2
    assert len(response.context["job_postings"].object_list) == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "active, href",
    [
        (True, INDEX_JOB_POSTINGS_URL),
        (False, f"{NEW_UPCOMING_FEATURE_NOTIFICATION_URL}?feature=stage"),
    ],
)
def test_beneficiary_home_links_job_postings_according_to_switch(client, active, href):
    """Both the home card and the sidebar link there."""
    with override_switch("internships", active=active):
        html = client.get(reverse("home")).content.decode()

    assert html.count(f'href="{href}"') == 2


INDEX_EVENTS_URL = "/evenements/"


def approved_event(pro, **overrides):

    return build_event(pro, **{"status": Event.Status.APPROVED, **overrides})


def other_pro(valid_pro_model_data):
    """A pro who is not the author of the fixture events."""

    pro = Pro(**{**valid_pro_model_data, "username": "bea@example.com"})
    pro.save()
    return pro


@pytest.fixture
def salon(pro):
    event = approved_event(pro, title="Salon des métiers du numérique")
    event.save()
    return event


@pytest.mark.django_db
def test_index_events_is_open_to_anonymous_visitors(client, salon):
    response = client.get(INDEX_EVENTS_URL)

    assert response.status_code == 200
    assert salon.title.encode() in response.content


@pytest.mark.django_db
def test_index_events_hides_events_awaiting_validation(client, event):
    """The `event` fixture is PENDING: only approved events reach the page."""
    response = client.get(INDEX_EVENTS_URL)

    assert event.title.encode() not in response.content


@pytest.mark.django_db
def test_index_events_hides_rejected_events(client, pro):
    approved_event(pro, title="Forum annulé", status=Event.Status.REJECTED).save()

    assert b"Forum annul" not in client.get(INDEX_EVENTS_URL).content


@pytest.mark.django_db
def test_index_events_hides_past_events(client, pro):
    today = timezone.localdate()
    approved_event(
        pro,
        title="Hackathon de l'an dernier",
        start_date=today - timedelta(days=3),
        end_date=today - timedelta(days=1),
    ).save()

    assert b"an dernier" not in client.get(INDEX_EVENTS_URL).content


@pytest.mark.django_db
def test_index_events_lists_from_the_nearest_to_the_furthest(client, pro):
    today = timezone.localdate()
    for title, days in [("Dans deux mois", 60), ("Dans cinq jours", 5), ("Dans un mois", 30)]:
        approved_event(
            pro,
            title=title,
            start_date=today + timedelta(days=days),
            end_date=today + timedelta(days=days),
        ).save()

    content = client.get(INDEX_EVENTS_URL).content

    assert (
        content.index(b"Dans cinq jours")
        < content.index(b"Dans un mois")
        < content.index(b"Dans deux mois")
    )


@pytest.mark.django_db
def test_index_events_cards_link_to_the_event_detail_page(client, salon):
    content = client.get(INDEX_EVENTS_URL).content

    assert reverse("show_event", args=[salon.slug]).encode() in content


@pytest.mark.django_db
def test_index_events_marks_the_events_a_beneficiary_already_saved(client, beneficiary, salon):
    SavedEvent.objects.toggle(event=salon, beneficiary=beneficiary)
    client.force_login(beneficiary)

    response = client.get(INDEX_EVENTS_URL)

    assert response.context["events"][0].saved is True
    assert b'aria-pressed="true"' in response.content


@pytest.mark.django_db
def test_index_events_leaves_an_unsaved_event_unmarked(client, beneficiary, salon):
    client.force_login(beneficiary)

    response = client.get(INDEX_EVENTS_URL)

    assert response.context["events"][0].saved is False
    assert b'aria-pressed="false"' in response.content


@pytest.mark.django_db
def test_index_events_saved_flag_costs_no_query_per_event(client, beneficiary, pro):
    """Four events must cost what one costs: the flag is annotated, never fetched per row.

    A first render warms the cache of the switches the layout reads."""

    approved_event(pro, title="Événement 0").save()
    client.force_login(beneficiary)
    client.get(INDEX_EVENTS_URL)
    with CaptureQueriesContext(connection) as one_event:
        client.get(INDEX_EVENTS_URL)

    for index in range(1, 4):
        approved_event(pro, title=f"Événement {index}").save()
    with CaptureQueriesContext(connection) as four_events:
        client.get(INDEX_EVENTS_URL)

    assert len(four_events.captured_queries) == len(one_event.captured_queries)


@pytest.mark.django_db
def test_index_events_bookmark_posts_to_update_saved_event(client, beneficiary, salon):
    client.force_login(beneficiary)

    content = client.get(INDEX_EVENTS_URL).content

    assert reverse("update_saved_event", args=[salon.pk]).encode() in content


@pytest.mark.django_db
def test_index_events_anonymous_bookmark_opens_the_signup_modal(client, salon):
    content = client.get(INDEX_EVENTS_URL).content

    assert reverse("create_saved_event_modal", args=[salon.pk]).encode() in content


@pytest.mark.django_db
def test_index_events_gives_a_connected_pro_no_bookmark_at_all(client, pro, salon):
    client.force_login(pro)

    content = client.get(INDEX_EVENTS_URL).content

    assert reverse("create_saved_event_modal", args=[salon.pk]).encode() not in content
    assert b"#bookmark" not in content


@pytest.mark.django_db
def test_index_events_cards_show_the_default_image_unframed(client, salon):
    content = client.get(INDEX_EVENTS_URL).content.decode()

    assert 'src="/static/images/events/guidance/open_house.webp"' in content
    assert "bg-" not in _image_box_classes(content, "card")


@pytest.mark.django_db
def test_index_events_cards_letterbox_an_uploaded_image_in_the_category_color(client, pro):
    approved_event(pro, image="events/abc.png", image_alt="Une porte ouverte").save()

    content = client.get(INDEX_EVENTS_URL).content.decode()

    assert 'src="/media/events/abc.png"' in content
    assert 'alt="Une porte ouverte"' in content
    assert "bg-green-500" in _image_box_classes(content, "card")


@pytest.mark.django_db
def test_index_events_shows_eighteen_events_and_a_link_to_the_next_page(client, pro):
    for index in range(20):
        approved_event(pro, title=f"Événement {index:02d}").save()

    response = client.get(INDEX_EVENTS_URL)

    assert len(response.context["events"].object_list) == 18
    assert b'href="?page=2"' in response.content


@pytest.mark.django_db
def test_index_events_serves_the_page_asked_for(client, pro):
    for index in range(20):
        approved_event(pro, title=f"Événement {index:02d}").save()

    response = client.get(INDEX_EVENTS_URL, {"page": 2})

    assert response.status_code == 200
    assert response.context["events"].number == 2
    assert len(response.context["events"].object_list) == 2
    assert b'aria-current="page"' in response.content


@pytest.mark.django_db
def test_index_events_hides_the_pagination_when_one_page_is_enough(client, salon):
    assert b"join-item" not in client.get(INDEX_EVENTS_URL).content


@pytest.mark.django_db
def test_index_events_falls_back_to_the_first_page_on_a_bogus_number(client, salon):
    response = client.get(INDEX_EVENTS_URL, {"page": "banane"})

    assert response.status_code == 200
    assert response.context["events"].number == 1


@pytest.mark.django_db
def test_update_saved_event_saves_the_event_for_the_beneficiary(client, beneficiary, salon):
    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_event", args=[salon.pk]))

    assert response.status_code == 200
    assert SavedEvent.objects.count() == 1
    assert b'aria-pressed="true"' in response.content
    assert b"text-blue-500" in response.content


@pytest.mark.django_db
def test_update_saved_event_twice_takes_the_event_back_out(client, beneficiary, salon):
    client.force_login(beneficiary)
    url = reverse("update_saved_event", args=[salon.pk])
    client.post(url)

    response = client.post(url)

    assert SavedEvent.objects.count() == 0
    assert b'aria-pressed="false"' in response.content


@pytest.mark.django_db
def test_update_saved_event_twice_leaves_the_bookmark_transparent(client, beneficiary, salon):
    client.force_login(beneficiary)
    url = reverse("update_saved_event", args=[salon.pk])
    client.post(url)

    response = client.post(url)

    assert b"text-blue-500" not in response.content


@pytest.mark.django_db
def test_update_saved_event_rejects_a_get(client, beneficiary, salon):
    client.force_login(beneficiary)

    response = client.get(reverse("update_saved_event", args=[salon.pk]))

    assert response.status_code == 405


@pytest.mark.django_db
def test_update_saved_event_requires_a_login(client, salon):
    response = client.post(reverse("update_saved_event", args=[salon.pk]))

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]


@pytest.mark.django_db
def test_update_saved_event_is_closed_to_pros(client, pro, salon):
    client.force_login(pro)

    response = client.post(reverse("update_saved_event", args=[salon.pk]))

    assert response.status_code == 404
    assert SavedEvent.objects.count() == 0


@pytest.mark.django_db
def test_update_saved_event_ignores_an_event_awaiting_validation(client, beneficiary, event):
    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_event", args=[event.pk]))

    assert response.status_code == 404
    assert SavedEvent.objects.count() == 0


@pytest.mark.django_db
def test_create_saved_event_modal_offers_signing_up_and_logging_in(client, salon):
    response = client.get(reverse("create_saved_event_modal", args=[salon.pk]))

    assert response.status_code == 200
    assert b"Rejoins le club TechPourToutes" in response.content
    assert reverse("new_beneficiary_inscription_funnel").encode() in response.content
    assert reverse("login_request").encode() in response.content


@pytest.mark.django_db
def test_create_saved_event_modal_carries_the_event_into_both_ways_in(client, salon):
    content = client.get(reverse("create_saved_event_modal", args=[salon.pk])).content.decode()

    assert f"{reverse('new_beneficiary_inscription_funnel')}?saved_event={salon.pk}" in content
    assert f"{reverse('login_request')}?saved_event={salon.pk}" in content


@pytest.mark.django_db
def test_create_saved_event_modal_ignores_an_event_awaiting_validation(client, event):
    assert client.get(reverse("create_saved_event_modal", args=[event.pk])).status_code == 404


@pytest.mark.django_db
def test_show_event_renders_the_event(client, salon):
    response = client.get(reverse("show_event", args=[salon.slug]))

    assert response.status_code == 200
    assert salon.title.encode() in response.content


@pytest.mark.django_db
def test_show_event_shows_the_uploaded_image_with_its_alternative_text(client, pro):
    event = approved_event(pro, image="events/abc.png", image_alt="Une porte ouverte")
    event.save()

    content = client.get(reverse("show_event", args=[event.slug])).content.decode()

    assert 'src="/media/events/abc.png"' in content
    assert 'alt="Une porte ouverte"' in content


@pytest.mark.django_db
def test_show_event_falls_back_to_the_default_image_of_its_category(client, salon):
    content = client.get(reverse("show_event", args=[salon.slug])).content.decode()

    assert 'src="/static/images/events/guidance/open_house.webp"' in content
    assert 'alt=""' in content
    assert "Crédit" not in content


def _image_box_classes(content, placement):
    return re.search(rf'data-event-image="{placement}" class="([^"]*)"', content)[1]


@pytest.mark.django_db
def test_show_event_letterboxes_an_uploaded_image_in_the_category_color(client, pro):
    event = approved_event(pro, image="events/abc.png")
    event.save()

    content = client.get(reverse("show_event", args=[event.slug])).content.decode()

    assert "bg-green-500" in _image_box_classes(content, "top")
    assert "bg-green-500" in _image_box_classes(content, "side")


@pytest.mark.django_db
def test_show_event_leaves_the_default_image_unframed_beside_the_card(client, salon):
    """On top, the frame is the colour of the header band anyway."""
    content = client.get(reverse("show_event", args=[salon.slug])).content.decode()

    assert "bg-green-500" in _image_box_classes(content, "top")
    assert "bg-" not in _image_box_classes(content, "side")
    assert "shadow-box" not in _image_box_classes(content, "side")


@pytest.mark.django_db
def test_show_event_centers_the_default_image_vertically_beside_the_card(client, salon):
    content = client.get(reverse("show_event", args=[salon.slug])).content.decode()

    assert 'class="w-full h-full object-contain object-right drop-shadow-box"' in content


@pytest.mark.django_db
def test_show_event_credits_the_uploaded_image(client, pro):
    event = approved_event(pro, image="events/abc.png", image_credit="Jane Doe")
    event.save()

    content = client.get(reverse("show_event", args=[event.slug])).content.decode()

    assert "Crédit : Jane Doe" in content


@pytest.mark.django_db
def test_show_event_makes_the_links_in_the_description_clickable(client, pro):
    event = approved_event(
        pro,
        title="Salon avec un lien",
        description="Programme sur https://techpourtoutes.io\n<b>pas du gras</b>",
    )
    event.save()

    content = client.get(reverse("show_event", args=[event.slug])).content.decode()

    anchor = content[content.index('<a href="https://techpourtoutes.io"') :].split("</a>")[0]
    assert 'target="_blank"' in anchor
    assert 'rel="nofollow noopener noreferrer"' in anchor
    assert "underline" in anchor
    # The description goes through `linebreaksbr`: the icon has to come out of it in one piece.
    assert "#external-link" in anchor
    assert "<br>" not in anchor
    # What surrounds the link is still escaped, and the line break still becomes a <br>.
    assert "<b>pas du gras</b>" not in content
    assert "&lt;b&gt;pas du gras&lt;/b&gt;" in content
    assert "<br>" in content


@pytest.mark.django_db
def test_show_event_shows_the_minutes_of_the_opening_hours(client, pro):
    event = approved_event(pro, start_time=time(9, 30), end_time=time(17, 45))
    event.save()

    content = client.get(reverse("show_event", args=[event.slug])).content.decode()

    assert "entre 9h30 et 17h45" in content


@pytest.mark.django_db
def test_show_event_hides_events_awaiting_validation(client, event):
    response = client.get(reverse("show_event", args=[event.slug]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_show_event_shows_the_city_tag_and_address_for_a_physical_event(client, pro):
    physical = approved_event(
        pro,
        location_type=Event.LocationType.PHYSICAL,
        address="8 Boulevard du Port",
        postal_code="80000",
        city="Amiens",
        longitude=2.29009,
        latitude=49.897443,
    )
    physical.save()

    content = client.get(reverse("show_event", args=[physical.slug])).content.decode()

    assert "Amiens" in content
    assert "Adresse" in content
    assert "8 Boulevard du Port" in content


@pytest.mark.django_db
def test_show_event_hides_the_city_tag_and_shows_online_for_an_online_event(client, pro):
    online = approved_event(
        pro,
        location_type=Event.LocationType.ONLINE,
        city="",
        online_url="https://meet.example.com/abc",
    )
    online.save()

    content = client.get(reverse("show_event", args=[online.slug])).content.decode()

    assert "En ligne" in content
    assert "Adresse" not in content
    assert "https://meet.example.com/abc" in content


@pytest.mark.django_db
def test_show_event_shows_no_cta_for_an_open_event(client, pro):
    open_event = approved_event(pro, access_type=Event.AccessType.OPEN)
    open_event.save()

    content = client.get(reverse("show_event", args=[open_event.slug])).content

    assert reverse("show_participation_modal", args=[open_event.pk]).encode() not in content


@pytest.mark.django_db
def test_show_event_shows_a_participate_cta_for_a_registration_event(client, pro):
    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()

    response = client.get(reverse("show_event", args=[registration.slug]))

    assert "Participer" in response.content.decode()
    assert reverse("show_participation_modal", args=[registration.pk]).encode() in response.content


@pytest.mark.django_db
def test_show_event_shows_a_candidacy_cta_for_a_candidacy_event(client, pro):
    candidacy = approved_event(pro, access_type=Event.AccessType.CANDIDACY)
    candidacy.save()

    response = client.get(reverse("show_event", args=[candidacy.slug]))

    assert "Candidater" in response.content.decode()
    assert reverse("show_participation_modal", args=[candidacy.pk]).encode() in response.content


@pytest.mark.django_db
def test_show_event_shows_the_participation_cta_to_a_connected_pro(
    client, pro, valid_pro_model_data
):
    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()
    client.force_login(other_pro(valid_pro_model_data))

    content = client.get(reverse("show_event", args=[registration.slug])).content

    assert reverse("show_participation_modal", args=[registration.pk]).encode() in content


@pytest.mark.django_db
def test_show_event_lets_the_author_open_her_event_awaiting_validation(client, pro, event):
    client.force_login(pro)

    response = client.get(reverse("show_event", args=[event.slug]))

    assert response.status_code == 200
    assert event.title in response.content.decode()


@pytest.mark.django_db
def test_show_event_hides_an_event_awaiting_validation_from_another_pro(
    client, event, valid_pro_model_data
):
    client.force_login(other_pro(valid_pro_model_data))

    assert client.get(reverse("show_event", args=[event.slug])).status_code == 404


@pytest.mark.django_db
def test_show_event_hides_an_event_awaiting_validation_from_a_beneficiary(
    client, beneficiary, event
):
    client.force_login(beneficiary)

    assert client.get(reverse("show_event", args=[event.slug])).status_code == 404


@pytest.mark.django_db
def test_show_event_lets_a_staff_member_open_an_event_awaiting_validation(client, event):
    staff = User.objects.create_user(
        username="staff@example.com",
        email="staff@example.com",
        first_name="Ada",
        last_name="Moderatrice",
        is_staff=True,
    )
    client.force_login(staff)

    assert client.get(reverse("show_event", args=[event.slug])).status_code == 200


@pytest.mark.django_db
def test_show_event_offers_the_author_a_link_to_edit_instead_of_participating(client, pro):
    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()
    client.force_login(pro)

    content = client.get(reverse("show_event", args=[registration.slug])).content.decode()

    assert "Modifier" in content
    assert reverse("edit_event", args=[registration.pk]) in content
    assert reverse("show_participation_modal", args=[registration.pk]) not in content


@pytest.mark.django_db
def test_show_event_offers_the_author_a_link_to_edit_an_event_open_to_all(client, pro):
    """The edit CTA does not hang off the registration link: an open event carries it too."""

    open_event = approved_event(pro, access_type=Event.AccessType.OPEN)
    open_event.save()
    client.force_login(pro)

    content = client.get(reverse("show_event", args=[open_event.slug])).content.decode()

    assert reverse("edit_event", args=[open_event.pk]) in content


@pytest.mark.django_db
def test_show_event_hides_every_cta_once_the_event_has_ended(client, beneficiary, pro):

    client.force_login(beneficiary)
    yesterday = timezone.localdate() - timedelta(days=1)
    past = approved_event(
        pro,
        access_type=Event.AccessType.REGISTRATION,
        start_date=yesterday,
        end_date=yesterday,
        end_time=time(18, 0),
    )
    past.save()

    response = client.get(reverse("show_event", args=[past.slug]))

    assert reverse("show_participation_modal", args=[past.pk]).encode() not in response.content
    assert reverse("update_saved_event", args=[past.pk]).encode() not in response.content


@pytest.mark.django_db
def test_show_event_gives_a_connected_pro_no_bookmark_at_all(client, pro, salon):
    client.force_login(pro)

    content = client.get(reverse("show_event", args=[salon.slug])).content

    assert reverse("create_saved_event_modal", args=[salon.pk]).encode() not in content
    assert reverse("update_saved_event", args=[salon.pk]).encode() not in content


@pytest.mark.django_db
def test_show_event_anonymous_bookmark_opens_the_signup_modal(client, salon):
    content = client.get(reverse("show_event", args=[salon.slug])).content

    assert reverse("create_saved_event_modal", args=[salon.pk]).encode() in content


@pytest.mark.django_db
def test_show_event_marks_an_already_saved_event(client, beneficiary, salon):
    SavedEvent.objects.toggle(event=salon, beneficiary=beneficiary)
    client.force_login(beneficiary)

    content = client.get(reverse("show_event", args=[salon.slug])).content

    assert b'aria-pressed="true"' in content


@pytest.mark.django_db
def test_update_saved_event_with_label_shows_a_labeled_button(client, beneficiary, salon):
    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_event", args=[salon.pk]), {"label": "true"})

    assert "Retirer de mes événements" in response.content.decode()


@pytest.mark.django_db
def test_update_saved_event_with_label_shows_the_saved_confirmation(client, beneficiary, salon):
    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_event", args=[salon.pk]), {"label": "true"})

    assert "Événement enregistré" in response.content.decode()


@pytest.mark.django_db
def test_update_saved_event_without_label_hides_the_labeled_button(client, beneficiary, salon):
    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_event", args=[salon.pk]))

    assert "Retirer de mes événements" not in response.content.decode()


@pytest.mark.django_db
def test_update_saved_event_removing_a_labeled_bookmark_shows_the_removed_confirmation(
    client, beneficiary, salon
):
    client.force_login(beneficiary)
    url = reverse("update_saved_event", args=[salon.pk])
    client.post(url, {"label": "true"})

    response = client.post(url, {"label": "true"})

    content = response.content.decode()
    assert "Événement retiré" in content
    assert "Événement enregistré" not in content
    assert "Ajouter à mes événements" in content


@pytest.mark.django_db
def test_show_participation_modal_offers_the_external_link_for_registration(client, pro):
    registration = approved_event(
        pro,
        access_type=Event.AccessType.REGISTRATION,
        registration_url="https://example.com/inscription",
    )
    registration.save()

    response = client.get(reverse("show_participation_modal", args=[registration.pk]))

    assert response.status_code == 200
    assert "pour t'inscrire" in response.content.decode()
    assert b"https://example.com/inscription" in response.content


@pytest.mark.django_db
def test_show_participation_modal_offers_the_external_link_for_candidacy(client, pro):
    candidacy = approved_event(
        pro,
        access_type=Event.AccessType.CANDIDACY,
        registration_url="https://example.com/candidature",
    )
    candidacy.save()

    response = client.get(reverse("show_participation_modal", args=[candidacy.pk]))

    assert "pour candidater" in response.content.decode()
    assert b"https://example.com/candidature" in response.content


@pytest.mark.django_db
def test_show_participation_modal_offers_saving_the_event_to_a_connected_beneficiary(
    client, beneficiary, pro
):
    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()
    client.force_login(beneficiary)

    response = client.get(reverse("show_participation_modal", args=[registration.pk]))

    assert reverse("update_saved_event", args=[registration.pk]).encode() in response.content


@pytest.mark.django_db
def test_show_participation_modal_hides_saving_from_an_anonymous_visitor(client, pro):
    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()

    response = client.get(reverse("show_participation_modal", args=[registration.pk]))

    assert reverse("update_saved_event", args=[registration.pk]).encode() not in response.content


@pytest.mark.django_db
def test_show_participation_modal_hides_saving_from_a_connected_pro(client, pro):
    registration = approved_event(pro, access_type=Event.AccessType.REGISTRATION)
    registration.save()
    client.force_login(pro)

    response = client.get(reverse("show_participation_modal", args=[registration.pk]))

    assert reverse("update_saved_event", args=[registration.pk]).encode() not in response.content


@pytest.mark.django_db
def test_show_participation_modal_ignores_an_event_awaiting_validation(client, event):
    response = client.get(reverse("show_participation_modal", args=[event.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_show_event_back_link_keeps_the_listing_page_and_filters(client, salon):
    response = client.get(
        reverse("show_event", args=[salon.slug]),
        HTTP_REFERER=f"http://testserver{INDEX_EVENTS_URL}?page=3&q=hackathon",
    )

    assert response.context["back_url"] == f"{INDEX_EVENTS_URL}?page=3&q=hackathon"


@pytest.mark.django_db
def test_show_event_back_link_falls_back_to_the_bare_listing(client, salon):
    response = client.get(reverse("show_event", args=[salon.slug]))

    assert response.context["back_url"] == INDEX_EVENTS_URL


@pytest.mark.django_db
def test_show_event_back_link_keeps_the_pro_events_page(client, salon):
    response = client.get(
        reverse("show_event", args=[salon.slug]),
        HTTP_REFERER=f"http://testserver{reverse('index_pro_events')}",
    )

    assert response.context["back_url"] == reverse("index_pro_events")


@pytest.mark.django_db
def test_show_event_back_link_trusts_a_back_param_from_the_pro_events_page(client, salon):
    """The edit-event funnel redirects here with `?back=...` rather than a matching referer,
    since the previous page in the browser's history is the funnel itself."""
    response = client.get(
        reverse("show_event", args=[salon.slug]), {"back": reverse("index_pro_events")}
    )

    assert response.context["back_url"] == reverse("index_pro_events")


@pytest.mark.django_db
def test_show_event_back_link_ignores_an_unsafe_back_param(client, salon):
    response = client.get(
        reverse("show_event", args=[salon.slug]),
        {"back": "https://evil.example.com/mes-evenements/"},
    )

    assert response.context["back_url"] == INDEX_EVENTS_URL


@pytest.mark.django_db
def test_show_event_back_link_ignores_a_referer_from_anywhere_else(client, salon):
    response = client.get(
        reverse("show_event", args=[salon.slug]),
        HTTP_REFERER="https://evil.example.com/evenements/?page=3",
    )

    assert response.context["back_url"] == INDEX_EVENTS_URL


@pytest.mark.django_db
def test_update_saved_event_swaps_every_bookmark_of_the_event(client, beneficiary, salon):
    """The detail page shows the bookmark twice and the modal a third time: one toggle from
    any of them has to leave the others in the same state."""
    client.force_login(beneficiary)

    content = client.post(reverse("update_saved_event", args=[salon.pk])).content.decode()

    assert f"hx-swap-oob='outerHTML:[data-bookmark=\"{salon.pk}\"]'" in content


@pytest.mark.django_db
def test_index_makeuses_shows_a_card_per_project(client):
    project = build_makeuse_project()
    project.image.name = "makeuse_projects/visuel.webp"
    project.save()

    content = client.get(reverse("index_makeuses")).content.decode()

    assert "Une appli pour trouver un stage" in content
    assert "Application mobile" in content
    assert "Hedy Lamarr" in content
    assert project.image.url in content


@pytest.mark.django_db
def test_index_makeuses_cards_take_the_color_of_their_category(client):
    project = build_makeuse_project(category=MakeuseProject.Category.DATA_AND_AI)
    project.image.name = "makeuse_projects/visuel.webp"
    project.save()

    content = client.get(reverse("index_makeuses")).content.decode()

    assert "bg-green-500" in content
    assert "bg-purple-500" not in content


@pytest.mark.django_db
def test_index_makeuses_card_without_image_shows_none(client):
    build_makeuse_project().save()

    content = client.get(reverse("index_makeuses")).content.decode()

    assert "Hedy Lamarr" in content
    assert "data-makeuse-project-image" not in content


@pytest.mark.django_db
def test_index_makeuses_lists_the_latest_project_first(client):
    build_makeuse_project(title="Le premier projet").save()
    build_makeuse_project(title="Le dernier projet").save()

    content = client.get(reverse("index_makeuses")).content.decode()

    assert content.index("Le dernier projet") < content.index("Le premier projet")


@pytest.mark.django_db
def test_index_makeuses_shows_six_projects_and_a_link_to_the_next_page(client):
    for index in range(8):
        build_makeuse_project(title=f"Projet {index:02d}").save()

    response = client.get(reverse("index_makeuses"))

    assert len(response.context["makeuse_projects"].object_list) == 6
    assert b'href="?page=2#projets"' in response.content


@pytest.mark.django_db
def test_index_makeuses_pagination_stays_on_the_projects(client):
    """Paging swaps the projects alone, back at the top of their list; without JavaScript,
    the link's anchor still lands there."""
    for index in range(8):
        build_makeuse_project(title=f"Projet {index:02d}").save()

    content = client.get(reverse("index_makeuses")).content.decode()

    assert 'id="projets"' in content
    assert 'href="?page=2#projets"' in content
    assert 'hx-get="?page=2"' in content
    assert 'hx-select="#projets"' in content
    assert 'hx-target="#projets"' in content
    assert 'hx-swap="outerHTML show:#projets:top"' in content
    assert 'hx-push-url="true"' in content


@pytest.mark.django_db
def test_index_makeuses_serves_the_page_asked_for(client):
    for index in range(8):
        build_makeuse_project(title=f"Projet {index:02d}").save()

    response = client.get(reverse("index_makeuses"), {"page": 2})

    assert response.context["makeuse_projects"].number == 2
    assert len(response.context["makeuse_projects"].object_list) == 2


@pytest.mark.django_db
def test_index_makeuses_cards_link_to_the_project_detail_page(client):
    project = build_makeuse_project()
    project.save()

    content = client.get(reverse("index_makeuses")).content.decode()

    assert f'href="{reverse("show_makeuse_project", args=[project.slug])}"' in content
    assert 'aria-label="Voir le projet Une appli pour trouver un stage"' in content


@pytest.mark.django_db
def test_show_makeuse_project_shows_the_whole_project(client):
    project = build_makeuse_project(demo_url="https://example.com/demo")
    project.save()

    content = client.get(reverse("show_makeuse_project", args=[project.slug])).content.decode()

    assert "Une appli pour trouver un stage" in content
    assert "Application mobile" in content
    assert "Hedy Lamarr" in content
    assert 'href="mailto:hedy@example.com"' in content
    assert 'href="https://example.com/demo"' in content
    assert "Rapprocher les lycéennes des entreprises du quartier." in content
    assert "Terminale STI2D à Amiens." in content
    assert "Des entretiens, puis un prototype Figma." in content
    assert "Le volley et le dessin." in content


@pytest.mark.django_db
def test_show_makeuse_project_reads_the_creator_from_her_account(client, beneficiary):
    project = build_makeuse_project(beneficiary=beneficiary, creator_name="", contact_email="")
    project.save()

    content = client.get(reverse("show_makeuse_project", args=[project.slug])).content.decode()

    assert "Jade Petit" in content
    assert 'href="mailto:jade@example.com"' in content


@pytest.mark.django_db
def test_index_makeuses_cards_read_the_creator_from_her_account(client, beneficiary):
    build_makeuse_project(beneficiary=beneficiary, creator_name="", contact_email="").save()

    content = client.get(reverse("index_makeuses")).content.decode()

    assert "Jade Petit" in content


@pytest.mark.django_db
def test_index_makeuses_reads_the_creators_without_a_query_per_card(client, beneficiary):
    linked = {"beneficiary": beneficiary, "creator_name": "", "contact_email": ""}
    build_makeuse_project(title="Projet 0", **linked).save()
    client.get(reverse("index_makeuses"))
    with CaptureQueriesContext(connection) as one_project:
        client.get(reverse("index_makeuses"))

    for index in range(1, 4):
        build_makeuse_project(title=f"Projet {index}", **linked).save()
    with CaptureQueriesContext(connection) as four_projects:
        client.get(reverse("index_makeuses"))

    assert len(four_projects.captured_queries) == len(one_project.captured_queries)


@pytest.mark.django_db
def test_show_makeuse_project_takes_the_color_of_its_category(client):
    project = build_makeuse_project(category=MakeuseProject.Category.DATA_AND_AI)
    project.image.name = "makeuse_projects/visuel.webp"
    project.save()

    content = client.get(reverse("show_makeuse_project", args=[project.slug])).content.decode()

    assert "bg-green-500" in content
    assert "bg-purple-500" not in content


@pytest.mark.django_db
def test_show_makeuse_project_without_demo_shows_no_demo_link(client):
    project = build_makeuse_project()
    project.save()

    content = client.get(reverse("show_makeuse_project", args=[project.slug])).content.decode()

    assert "Hedy Lamarr" in content
    assert "Voir la démo" not in content


@pytest.mark.django_db
def test_show_makeuse_project_unknown_slug_returns_404(client):
    response = client.get(reverse("show_makeuse_project", args=["projet-inconnu"]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_show_makeuse_project_back_link_keeps_the_listing_page(client):
    project = build_makeuse_project()
    project.save()

    response = client.get(
        reverse("show_makeuse_project", args=[project.slug]),
        HTTP_REFERER=f"http://testserver{reverse('index_makeuses')}?page=2",
    )

    assert response.context["back_url"] == f"{reverse('index_makeuses')}?page=2#projets"


@pytest.mark.django_db
def test_show_makeuse_project_back_link_falls_back_to_the_bare_listing(client):
    project = build_makeuse_project()
    project.save()

    response = client.get(reverse("show_makeuse_project", args=[project.slug]))

    assert response.context["back_url"] == reverse("index_makeuses")


@pytest.mark.django_db
def test_show_makeuse_project_back_link_ignores_a_referer_from_anywhere_else(client):
    project = build_makeuse_project()
    project.save()

    response = client.get(
        reverse("show_makeuse_project", args=[project.slug]),
        HTTP_REFERER=f"http://testserver{INDEX_EVENTS_URL}?page=3",
    )

    assert response.context["back_url"] == reverse("index_makeuses")
