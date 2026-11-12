import re
from datetime import date, time, timedelta
from unittest.mock import patch
from urllib.parse import quote, urlencode

import pytest
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from waffle.testutils import override_switch

from techpourtoutes.models import (
    ClickedJobPosting,
    Event,
    JobPosting,
    MakeuseProject,
    Pro,
    SavedEvent,
    SavedJobPosting,
    User,
)
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
    job_posting = JobPosting(
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
    )
    job_posting.save()
    return job_posting


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
def test_index_job_postings_leaves_out_the_hidden_postings(client):
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    save_job_posting("Publiée", category)
    save_job_posting("Dépubliée", category, hidden=True)

    assert listed_titles(client.get(INDEX_JOB_POSTINGS_URL)) == {"Publiée"}


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_shows_every_domain_of_a_posting(client):
    save_job_posting(
        "Stage",
        JobPosting.Category.HIGHER_ED_INTERNSHIP,
        domains=[JobPosting.Domain.MATHEMATIQUES, JobPosting.Domain.SYSTEMES_ET_RESEAUX],
    )

    html = client.get(INDEX_JOB_POSTINGS_URL).content.decode()

    for label in ["Mathématiques", "Systèmes et réseaux"]:
        assert re.search(rf"#job-domain.*?<span>\s*{label}\s*</span>", html, re.DOTALL)


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_decodes_the_description_and_still_escapes_it(client):
    save_job_posting(
        "Stage",
        JobPosting.Category.HIGHER_ED_INTERNSHIP,
        description="<p>Stage&nbsp;: R&amp;D &eacute;quipe</p>"
        "&lt;script&gt;alert(1)&lt;/script&gt;",
    )

    html = client.get(INDEX_JOB_POSTINGS_URL).content.decode()

    assert "Stage\xa0: R&amp;D équipe&lt;script&gt;alert(1)&lt;/script&gt;" in html


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
        domains=[JobPosting.Domain.MATHEMATIQUES, JobPosting.Domain.SYSTEMES_ET_RESEAUX],
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


EVERY_PLACE = {"Brest", "Ajaccio", "Saint-Denis", "Londres", "Nulle part"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, expected",
    [
        ({"department": "29"}, {"Brest"}),
        ({"department": ["2A", "974"]}, {"Ajaccio", "Saint-Denis"}),
        ({"department": "99"}, {"Londres"}),
        ({"department": "97"}, EVERY_PLACE),
        ({}, EVERY_PLACE),
    ],
)
@override_switch("internships", active=True)
def test_index_job_postings_keeps_the_postings_of_any_ticked_department(client, query, expected):
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    for title, department in [
        ("Brest", "29"),
        ("Ajaccio", "2A"),
        ("Saint-Denis", "974"),
        ("Londres", "99"),
        ("Nulle part", ""),
    ]:
        save_job_posting(title, category, department_code=department)

    assert listed_titles(client.get(INDEX_JOB_POSTINGS_URL, query)) == expected


@pytest.mark.django_db
@override_switch("internships", active=True)
@pytest.mark.parametrize(
    "category, offers_apec_domains",
    [
        ("higher_ed_internship", True),
        ("apprenticeship", True),
        ("first_job", True),
        ("seconde_internship", False),
        ("troisieme_internship", False),
    ],
)
def test_index_job_postings_offers_the_domains_of_the_category(
    client, category, offers_apec_domains
):
    html = client.get(INDEX_JOB_POSTINGS_URL, {"category": category}).content.decode()

    for domain in JobPosting.Domain:
        offered = offers_apec_domains or domain not in JobPosting.APEC_DOMAINS
        assert (f'value="{domain.value}"' in html) == offered
        assert (str(domain.label) in html) == offered


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_ignores_an_apec_domain_ticked_on_a_pupils_tab(client):
    category = JobPosting.Category.TROISIEME_INTERNSHIP
    save_job_posting("Création", category, domains=[JobPosting.Domain.CREATION])
    save_job_posting("Électro", category, domains=[JobPosting.Domain.ELECTRONIQUE])

    response = client.get(INDEX_JOB_POSTINGS_URL, {"category": category, "domain": "creation"})

    assert listed_titles(response) == {"Création", "Électro"}


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
    assert re.findall(r'name="duration"\s+value="([^"]*)"', html) == (
        JobPosting.Duration.values if offered else []
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, expected",
    [
        ({"duration": "3_to_6_months"}, {"6 mois", "Sans durée"}),
        ({"duration": ["under_3_months", "over_12_months"]}, {"2 mois", "24 mois", "Sans durée"}),
        ({"duration": "inconnue"}, {"2 mois", "6 mois", "24 mois", "Sans durée"}),
        ({}, {"2 mois", "6 mois", "24 mois", "Sans durée"}),
    ],
)
@override_switch("internships", active=True)
def test_index_job_postings_keeps_the_postings_of_any_ticked_duration_and_those_without_one(
    client, query, expected
):
    for title, months in [("2 mois", 2), ("6 mois", 6), ("24 mois", 24), ("Sans durée", None)]:
        save_job_posting(title, JobPosting.Category.APPRENTICESHIP, duration_months=months)

    response = client.get(INDEX_JOB_POSTINGS_URL, {"category": "apprenticeship", **query})

    assert listed_titles(response) == expected


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_shows_the_duration_on_the_card(client):
    save_job_posting("Alternance", JobPosting.Category.APPRENTICESHIP, duration_months=24)

    html = client.get(INDEX_JOB_POSTINGS_URL, {"category": "apprenticeship"}).content.decode()

    assert re.search(r"<span>\s*24 mois\s*</span>", html)


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_hides_and_ignores_the_duration_filter_when_cdi_alone_is_ticked(
    client,
):
    """A CDI lasts as long as it lasts: alone, it leaves no duration to choose from."""
    save_job_posting("CDI", JobPosting.Category.FIRST_JOB, contract_type="cdi", duration_months=2)

    response = client.get(
        INDEX_JOB_POSTINGS_URL,
        {"category": "first_job", "contract_type": "cdi", "duration": "over_12_months"},
    )

    assert listed_titles(response) == {"CDI"}
    html = response.content.decode()
    assert re.search(r'id="job_posting_duration_filter"[^>]*style="display: none"', html)
    assert not re.search(r'name="duration"\s+value="[^"]*"\s+checked', html)


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_keeps_the_duration_filter_when_cdi_comes_with_another_contract(
    client,
):
    response = client.get(
        INDEX_JOB_POSTINGS_URL,
        {"category": "first_job", "contract_type": ["cdi", "cdd"], "duration": "over_12_months"},
    )

    html = response.content.decode()
    assert not re.search(r'id="job_posting_duration_filter"[^>]*style="display: none"', html)
    assert re.findall(r'name="duration"\s+value="([^"]*)"\s+checked', html) == ["over_12_months"]


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


def show_job_posting_url(job_posting):
    return reverse("show_job_posting", args=[job_posting.pk])


@pytest.mark.django_db
@override_switch("internships", active=False)
def test_show_job_posting_not_found_when_switch_inactive(client):
    job_posting = save_job_posting("Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP)

    assert client.get(show_job_posting_url(job_posting)).status_code == 404


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_not_found_once_unpublished(client):
    job_posting = save_job_posting("Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP, hidden=True)

    assert client.get(show_job_posting_url(job_posting)).status_code == 404


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_renders_the_posting(client):
    job_posting = save_job_posting(
        "Développeuse BI",
        JobPosting.Category.FIRST_JOB,
        contract_type=JobPosting.ContractType.CDD,
        description="<p>Tu <strong>développes</strong> des tableaux de bord.</p>",
        domains=[JobPosting.Domain.SYSTEMES_ET_RESEAUX],
        experience_level="Minimum 2 ans",
        salary="36 - 44 k€ brut annuel",
        duration_months=6,
        sector="Activités informatiques",
        street="12 rue de la Mer",
        postal_code="80000",
    )

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert "Développeuse BI" in html
    assert "<p>Tu <strong>développes</strong> des tableaux de bord.</p>" in html
    for shown in [
        "Systèmes et réseaux",
        "CDD",
        "Minimum 2 ans",
        "36 - 44 k€ brut annuel",
        "6 mois",
        "Activités informatiques",
        "12 rue de la Mer, 80000 Amiens",
    ]:
        assert shown in html
    assert "non indiqué" not in html


@pytest.mark.django_db
@pytest.mark.parametrize("category", ["higher_ed_internship", "apprenticeship", "first_job"])
@override_switch("internships", active=True)
def test_show_job_posting_leaves_out_the_position_status(client, category):
    """Apec says « Cadre du secteur privé » nearly every time, and an internship is a « Stage »."""
    job_posting = save_job_posting("Offre", category)

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert "Statut du poste" not in html


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_sizes_the_logo_without_a_stylesheet(client):
    job_posting = save_job_posting("Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP)

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert re.search(
        r'<img src="[^"]*job-posting-placeholder[^"]*"[^>]*width="70" height="70"', html
    )


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_puts_save_beside_back_and_apply_at_the_bottom_on_a_phone(client):
    """On a phone the save button sits beside the back one, above the title, and the apply one
    in the bar fixed at the bottom: a screen reader reads them in the order they are shown."""
    job_posting = save_job_posting("Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP)

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert html.index("Retour") < html.index("Enregistrer") < html.index("cherche une stagiaire")
    assert html.rindex("Postuler sur") > html.index("Descriptif de l’offre")


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_offers_no_save_button_to_a_signed_in_pro(client, pro):
    job_posting = save_job_posting("Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP)
    assert "Enregistrer" in client.get(show_job_posting_url(job_posting)).content.decode()

    client.force_login(pro)

    assert "Enregistrer" not in client.get(show_job_posting_url(job_posting)).content.decode()


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_says_what_the_partner_did_not_give(client):
    job_posting = save_job_posting("Alternance", JobPosting.Category.APPRENTICESHIP)

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    for label in [
        "Durée",
        "Niveau d’expérience",
        "Salaire",
        "Secteur",
    ]:
        assert re.search(rf"{label}&nbsp;:</dt>\s*<dd[^>]*>\s*non indiqué", html), label


@pytest.mark.django_db
@pytest.mark.parametrize(
    "category, mention",
    [
        ("higher_ed_internship", "Numeum cherche une stagiaire au poste de&nbsp;:"),
        ("apprenticeship", "Numeum cherche une alternante au poste de&nbsp;:"),
        ("first_job", "Numeum recrute au poste de&nbsp;:"),
        ("seconde_internship", "Numeum propose un stage d’observation"),
        ("troisieme_internship", "Numeum propose un stage d’observation"),
    ],
)
@override_switch("internships", active=True)
def test_show_job_posting_introduces_the_company_according_to_the_category(
    client, category, mention
):
    job_posting = save_job_posting("Offre", category)

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert mention in html
    assert f"bg-{JobPosting.CATEGORY_COLORS[category]}-500" in html


@pytest.mark.django_db
@pytest.mark.parametrize("category", ["seconde_internship", "troisieme_internship"])
@override_switch("internships", active=True)
def test_show_job_posting_shows_a_pupil_the_period_and_nothing_about_the_job(client, category):
    job_posting = save_job_posting(
        "Stage", category, starts_on=date(2027, 6, 12), ends_on=date(2027, 6, 19)
    )

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert re.search(r"Date&nbsp;:</dt>\s*<dd[^>]*>\s*du 12 juin 2027 au 19 juin 2027", html)
    for label in ["Durée", "Salaire", "Secteur", "Date de début"]:
        assert label not in html


@pytest.mark.django_db
@pytest.mark.parametrize("category", ["higher_ed_internship", "apprenticeship", "first_job"])
@override_switch("internships", active=True)
def test_show_job_posting_leaves_out_the_start_date(client, category):
    job_posting = save_job_posting("Offre", category, starts_on=date(2027, 1, 1))

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert "Date de début" not in html
    assert "01/01/2027" not in html


@pytest.mark.django_db
@pytest.mark.parametrize(
    "contract_type, shown",
    [(JobPosting.ContractType.CDI, False), (JobPosting.ContractType.CDD, True)],
)
@override_switch("internships", active=True)
def test_show_job_posting_leaves_out_the_duration_of_a_cdi(client, contract_type, shown):
    job_posting = save_job_posting(
        "Développeuse", JobPosting.Category.FIRST_JOB, contract_type=contract_type
    )

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert ("Durée" in html) == shown


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_says_when_it_was_published(client):
    job_posting = save_job_posting(
        "Stage",
        JobPosting.Category.HIGHER_ED_INTERNSHIP,
        published_at=timezone.make_aware(timezone.datetime(2026, 10, 12, 10)),
    )

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert "Offre publiée le 12 octobre 2026" in html


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_says_when_it_was_last_updated(client):
    job_posting = save_job_posting(
        "Stage",
        JobPosting.Category.HIGHER_ED_INTERNSHIP,
        source_updated_at=timezone.make_aware(timezone.datetime(2026, 10, 14, 10)),
    )

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert "Offre mise à jour le 14 octobre 2026" in html
    assert "Offre publiée le" not in html


@pytest.mark.django_db
@pytest.mark.parametrize(
    "source, logo",
    [("apec", "images/apec_logo.jpg"), ("myfuture", "images/myfuture_logo.png")],
)
@override_switch("internships", active=True)
def test_show_job_posting_shows_the_logo_of_the_partner(client, source, logo):
    """The sentence beside it names the partner: the logo adds nothing for a screen reader."""
    job_posting = save_job_posting("Stage", JobPosting.Category.APPRENTICESHIP, source=source)

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert re.search(rf'<img src="/static/{logo}" alt=""', html)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "source, partner",
    [("apec", "l’Apec"), ("myfuture", "MyFuture")],
)
@override_switch("internships", active=True)
def test_show_job_posting_sends_her_to_the_partner_to_apply(client, source, partner):
    job_posting = save_job_posting(
        "Stage",
        JobPosting.Category.HIGHER_ED_INTERNSHIP,
        source=source,
        external_id="563753",
        published_at=timezone.make_aware(timezone.datetime(2026, 10, 13, 10)),
    )

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    application_modal_url = reverse("show_job_posting_application_modal", args=[job_posting.pk])
    assert re.search(
        rf'<button[^>]*hx-get="{application_modal_url}\?back=[^"]*"[^>]*>\s*<div[^>]*>'
        rf"\s*<svg[^>]*>.*?</svg>\s*Postuler sur {partner}",
        html,
        re.S,
    )
    assert "https://www.apec.fr/offre" not in html
    assert (
        "Cette offre ID 563753 a été publiée le 13 octobre 2026 sur le site de notre "
        f"partenaire, {partner}."
    ) in html


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_goes_back_to_the_listing_she_came_from(client):
    job_posting = save_job_posting("Stage", JobPosting.Category.APPRENTICESHIP)
    listing = f"{INDEX_JOB_POSTINGS_URL}?category=apprenticeship&page=2"

    response = client.get(show_job_posting_url(job_posting), HTTP_REFERER=listing)

    assert response.context["back_url"] == f"{listing}#offre-{job_posting.pk}"


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_goes_back_to_the_top_of_the_listing_without_one_to_return_to(client):
    job_posting = save_job_posting("Stage", JobPosting.Category.APPRENTICESHIP)

    response = client.get(show_job_posting_url(job_posting))

    assert response.context["back_url"] == INDEX_JOB_POSTINGS_URL


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_anchors_each_card_for_the_way_back(client):
    job_posting = save_job_posting("Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP)

    content = client.get(INDEX_JOB_POSTINGS_URL).content.decode()

    assert f'id="offre-{job_posting.pk}"' in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_is_never_served_from_the_browser_cache(client):
    """Back or forward would otherwise show the bookmarks as they were before a toggle."""
    response = client.get(INDEX_JOB_POSTINGS_URL)

    assert "no-store" in response["Cache-Control"]


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_is_never_served_from_the_browser_cache(client, job_posting):
    response = client.get(show_job_posting_url(job_posting))

    assert "no-store" in response["Cache-Control"]


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_bookmark_posts_to_update_saved_job_posting(
    client, beneficiary, job_posting
):
    client.force_login(beneficiary)

    response = client.get(INDEX_JOB_POSTINGS_URL, {"category": job_posting.category})

    assert response.context["job_postings"][0].saved is False
    content = response.content.decode()
    assert reverse("update_saved_job_posting", args=[job_posting.pk]) in content
    assert 'aria-pressed="false"' in content
    assert "text-neutral-0" in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_colours_the_bookmark_of_a_saved_posting_after_its_category(
    client, beneficiary
):
    job_posting = save_job_posting("Alternance", JobPosting.Category.APPRENTICESHIP)
    SavedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=beneficiary)
    client.force_login(beneficiary)

    response = client.get(INDEX_JOB_POSTINGS_URL, {"category": job_posting.category})

    assert response.context["job_postings"][0].saved is True
    content = response.content.decode()
    assert 'aria-pressed="true"' in content
    assert f'aria-label="Enregistrer l’offre {job_posting.title}"' in content
    assert "text-orange-500" in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_saved_flag_costs_no_query_per_posting(client, beneficiary):
    """Four postings must cost what one costs: the flag is annotated, never fetched per row.

    A first render warms the cache of the switches the layout reads."""
    save_job_posting("Stage 0", JobPosting.Category.HIGHER_ED_INTERNSHIP)
    client.force_login(beneficiary)
    client.get(INDEX_JOB_POSTINGS_URL)
    with CaptureQueriesContext(connection) as one_posting:
        client.get(INDEX_JOB_POSTINGS_URL)

    for index in range(1, 4):
        save_job_posting(f"Stage {index}", JobPosting.Category.HIGHER_ED_INTERNSHIP)
    with CaptureQueriesContext(connection) as four_postings:
        client.get(INDEX_JOB_POSTINGS_URL)

    assert len(four_postings.captured_queries) == len(one_posting.captured_queries)


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_anonymous_bookmark_opens_the_signup_modal(client, job_posting):
    content = client.get(
        INDEX_JOB_POSTINGS_URL, {"category": job_posting.category}
    ).content.decode()

    assert reverse("create_saved_job_posting_modal", args=[job_posting.pk]) in content
    assert reverse("update_saved_job_posting", args=[job_posting.pk]) not in content
    assert "aria-pressed" not in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_gives_a_connected_pro_no_bookmark_at_all(client, pro, job_posting):
    client.force_login(pro)

    content = client.get(
        INDEX_JOB_POSTINGS_URL, {"category": job_posting.category}
    ).content.decode()

    assert reverse("create_saved_job_posting_modal", args=[job_posting.pk]) not in content
    assert "#bookmark" not in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_bookmark_posts_to_update_saved_job_posting(
    client, beneficiary, job_posting
):
    client.force_login(beneficiary)

    content = client.get(show_job_posting_url(job_posting)).content.decode()

    assert reverse("update_saved_job_posting", args=[job_posting.pk]) in content
    assert 'aria-pressed="false"' in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_marks_an_already_saved_posting(client, beneficiary, job_posting):
    SavedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=beneficiary)
    client.force_login(beneficiary)

    content = client.get(show_job_posting_url(job_posting)).content.decode()

    assert 'aria-pressed="true"' in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_anonymous_bookmark_opens_the_signup_modal(client, job_posting):
    content = client.get(show_job_posting_url(job_posting)).content.decode()

    assert reverse("create_saved_job_posting_modal", args=[job_posting.pk]) in content
    assert reverse("update_saved_job_posting", args=[job_posting.pk]) not in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_gives_a_connected_pro_no_bookmark_at_all(client, pro, job_posting):
    client.force_login(pro)

    content = client.get(show_job_posting_url(job_posting)).content.decode()

    assert reverse("update_saved_job_posting", args=[job_posting.pk]) not in content
    assert reverse("create_saved_job_posting_modal", args=[job_posting.pk]) not in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_welcomes_her_to_the_club_once(client, beneficiary, job_posting):
    """Signing up to save an offer lands her back on it: the welcome waits for her there."""
    client.force_login(beneficiary)
    session = client.session
    session["show_welcome_modal"] = True
    session.save()

    assert "Bienvenue au club" in client.get(show_job_posting_url(job_posting)).content.decode()
    assert (
        "Bienvenue au club" not in client.get(show_job_posting_url(job_posting)).content.decode()
    )


def application_modal_url(job_posting):
    return reverse("show_job_posting_application_modal", args=[job_posting.pk])


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_application_modal_names_the_posting_and_sends_her_to_the_partner(
    client, job_posting
):
    content = client.get(application_modal_url(job_posting)).content.decode()

    assert "Tu vas être redirigée pour candidater" in content
    assert re.search(r"Opportunité&nbsp;:\s*<strong>Développeuse web</strong>", content)
    assert re.search(r"Entreprise&nbsp;:\s*<strong>Octo</strong>", content)
    assert re.search(
        r'<a href="https://www\.myfuture\.fr/offre/1"[^>]*target="_blank"[^>]*>.*?'
        r"Continuer sur le site externe",
        content,
        re.S,
    )


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_application_modal_offers_an_anonymous_visitor_to_save_the_posting(
    client, job_posting
):
    content = client.get(application_modal_url(job_posting)).content.decode()

    assert "Enregistrer l’opportunité" in content
    assert reverse("create_saved_job_posting_modal", args=[job_posting.pk]) in content
    assert reverse("create_clicked_job_posting", args=[job_posting.pk]) not in content
    assert "automatiquement enregistrée" not in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_application_modal_records_the_click_of_a_beneficiary(
    client, beneficiary, job_posting
):
    client.force_login(beneficiary)

    content = client.get(application_modal_url(job_posting)).content.decode()

    assert "L’opportunité sera automatiquement enregistrée dans ton compte." in content
    assert reverse("create_clicked_job_posting", args=[job_posting.pk]) in content
    assert reverse("update_saved_job_posting", args=[job_posting.pk]) not in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_application_modal_neither_saves_nor_records_for_a_pro(
    client, pro, job_posting
):
    client.force_login(pro)

    content = client.get(application_modal_url(job_posting)).content.decode()

    assert "Continuer sur le site externe" in content
    assert "automatiquement enregistrée" not in content
    assert reverse("create_clicked_job_posting", args=[job_posting.pk]) not in content
    assert reverse("create_saved_job_posting_modal", args=[job_posting.pk]) not in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_application_modal_ignores_an_unpublished_posting(client):
    job_posting = save_job_posting("Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP, hidden=True)

    assert client.get(application_modal_url(job_posting)).status_code == 404


@pytest.mark.django_db
@override_switch("internships", active=False)
def test_show_job_posting_application_modal_not_found_when_switch_inactive(client, job_posting):
    assert client.get(application_modal_url(job_posting)).status_code == 404


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_update_saved_job_posting_saves_the_posting_for_the_beneficiary(
    client, beneficiary, job_posting
):
    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_job_posting", args=[job_posting.pk]))

    assert response.status_code == 200
    assert list(beneficiary.saved_job_postings.all()) == [job_posting]
    content = response.content.decode()
    assert 'aria-pressed="true"' in content
    assert "Offre enregistrée" in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_update_saved_job_posting_twice_takes_the_posting_back_out(
    client, beneficiary, job_posting
):
    client.force_login(beneficiary)
    url = reverse("update_saved_job_posting", args=[job_posting.pk])
    client.post(url)

    response = client.post(url)

    assert SavedJobPosting.objects.count() == 0
    content = response.content.decode()
    assert 'aria-pressed="false"' in content
    assert "Offre retirée" in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_update_saved_job_posting_swaps_every_bookmark_of_the_posting(
    client, beneficiary, job_posting
):
    """The page and the application modal each show the bookmark: one toggle from either has
    to leave the other in the same state."""
    client.force_login(beneficiary)

    content = client.post(reverse("update_saved_job_posting", args=[job_posting.pk])).content

    assert f"hx-swap-oob='outerHTML:[data-bookmark=\"{job_posting.pk}\"]'" in content.decode()


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_update_saved_job_posting_from_a_card_swaps_the_card_bookmark_back_in(
    client, beneficiary, job_posting
):
    client.force_login(beneficiary)

    content = client.post(
        reverse("update_saved_job_posting", args=[job_posting.pk]), {"card": "true"}
    ).content.decode()

    assert "#bookmark_rosette" in content
    assert f"text-{job_posting.category_color}-500" in content
    assert "Enregistrée" not in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_update_saved_job_posting_rejects_a_get(client, beneficiary, job_posting):
    client.force_login(beneficiary)

    response = client.get(reverse("update_saved_job_posting", args=[job_posting.pk]))

    assert response.status_code == 405


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_update_saved_job_posting_requires_a_login(client, job_posting):
    response = client.post(reverse("update_saved_job_posting", args=[job_posting.pk]))

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_update_saved_job_posting_is_closed_to_pros(client, pro, job_posting):
    client.force_login(pro)

    response = client.post(reverse("update_saved_job_posting", args=[job_posting.pk]))

    assert response.status_code == 404
    assert SavedJobPosting.objects.count() == 0


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_update_saved_job_posting_ignores_an_unpublished_posting(client, beneficiary):
    job_posting = save_job_posting("Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP, hidden=True)
    client.force_login(beneficiary)

    response = client.post(reverse("update_saved_job_posting", args=[job_posting.pk]))

    assert response.status_code == 404
    assert SavedJobPosting.objects.count() == 0


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_create_saved_job_posting_modal_carries_the_posting_into_both_ways_in(client, job_posting):
    content = client.get(
        reverse("create_saved_job_posting_modal", args=[job_posting.pk])
    ).content.decode()

    assert "Rejoins le club TechPourToutes" in content
    assert (
        f"{reverse('new_beneficiary_inscription_funnel')}?saved_job_posting={job_posting.pk}"
        in content
    )
    assert f"{reverse('login_request')}?saved_job_posting={job_posting.pk}" in content


def _signed_in_on(client, user, url):
    """Sign in through the code mailed, as from a page: she lands on it with a welcome message."""
    client.post(reverse("login_request"), data={"email": user.email, "next": url})
    code = user.issue_login_code()
    return client.post(reverse("login_code"), data={"code": code}, follow=True)


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_shows_a_pending_message_once(client, beneficiary, job_posting):
    response = _signed_in_on(client, beneficiary, show_job_posting_url(job_posting))

    assert response.content.decode().count("Bienvenue sur le compte") == 1


JOB_POSTINGS_LISTING = "/stages-alternances-emplois/?q=data"


def _with_way_back(url, back):
    return f"{url}?{urlencode({'back': back})}"


def _assert_both_ways_in_go_back_to(content, saved, pk, back):
    """Closing the sign-up or the login funnel brings her back to `back`."""
    query = f"?{saved}={pk}&back={quote(back, safe='')}"
    assert f"{reverse('new_beneficiary_inscription_funnel')}{query}" in content
    assert f"{reverse('login_request')}{query}" in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_hands_the_page_and_its_listing_to_both_modals(client, job_posting):
    page_url = _with_way_back(
        show_job_posting_url(job_posting), f"{JOB_POSTINGS_LISTING}#offre-{job_posting.pk}"
    )

    content = client.get(
        show_job_posting_url(job_posting), HTTP_REFERER=f"http://testserver{JOB_POSTINGS_LISTING}"
    ).content.decode()

    back = f"?back={quote(page_url, safe='')}"
    application_modal = reverse("show_job_posting_application_modal", args=[job_posting.pk])
    assert content.count(f"{application_modal}{back}") == 2
    save_modal = reverse("create_saved_job_posting_modal", args=[job_posting.pk])
    assert content.count(f"{save_modal}{back}") == 2


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_show_job_posting_application_modal_hands_its_way_back_to_the_save_modal(
    client, job_posting
):
    page_url = _with_way_back(show_job_posting_url(job_posting), JOB_POSTINGS_LISTING)

    content = client.get(
        reverse("show_job_posting_application_modal", args=[job_posting.pk]), {"back": page_url}
    ).content.decode()

    save_modal = reverse("create_saved_job_posting_modal", args=[job_posting.pk])
    assert f"{save_modal}?back={quote(page_url, safe='')}" in content


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_create_saved_job_posting_modal_carries_the_way_back_it_is_given(client, job_posting):
    page_url = _with_way_back(show_job_posting_url(job_posting), JOB_POSTINGS_LISTING)

    content = client.get(
        reverse("create_saved_job_posting_modal", args=[job_posting.pk]), {"back": page_url}
    ).content.decode()

    _assert_both_ways_in_go_back_to(content, "saved_job_posting", job_posting.pk, page_url)


@pytest.mark.django_db
@override_switch("internships", active=True)
@pytest.mark.parametrize("query", [{}, {"back": "https://evil.example/"}])
def test_create_saved_job_posting_modal_goes_back_to_the_posting_by_default(
    client, job_posting, query
):
    content = client.get(
        reverse("create_saved_job_posting_modal", args=[job_posting.pk]), query
    ).content.decode()

    _assert_both_ways_in_go_back_to(
        content, "saved_job_posting", job_posting.pk, show_job_posting_url(job_posting)
    )


@pytest.mark.django_db
@override_switch("internships", active=True)
@pytest.mark.parametrize("fragment", ["", "#offre-une-autre"])
def test_create_saved_job_posting_modal_opened_from_a_card_goes_back_to_that_card(
    client, job_posting, fragment
):
    content = client.get(
        reverse("create_saved_job_posting_modal", args=[job_posting.pk]),
        HTTP_HX_CURRENT_URL=f"http://testserver{JOB_POSTINGS_LISTING}{fragment}",
    ).content.decode()

    _assert_both_ways_in_go_back_to(
        content,
        "saved_job_posting",
        job_posting.pk,
        f"{JOB_POSTINGS_LISTING}#offre-{job_posting.pk}",
    )


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_create_saved_job_posting_modal_ignores_an_unpublished_posting(client):
    job_posting = save_job_posting("Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP, hidden=True)

    response = client.get(reverse("create_saved_job_posting_modal", args=[job_posting.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_create_clicked_job_posting_records_the_click(client, beneficiary, job_posting):
    client.force_login(beneficiary)

    response = client.post(reverse("create_clicked_job_posting", args=[job_posting.pk]))

    assert response.status_code == 204
    assert list(beneficiary.clicked_job_postings.all()) == [job_posting]


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_create_clicked_job_posting_twice_keeps_the_click(client, beneficiary, job_posting):
    client.force_login(beneficiary)
    url = reverse("create_clicked_job_posting", args=[job_posting.pk])
    client.post(url)

    client.post(url)

    assert list(beneficiary.clicked_job_postings.all()) == [job_posting]


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_create_clicked_job_posting_rejects_a_get(client, beneficiary, job_posting):
    client.force_login(beneficiary)

    response = client.get(reverse("create_clicked_job_posting", args=[job_posting.pk]))

    assert response.status_code == 405


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_create_clicked_job_posting_requires_a_login(client, job_posting):
    response = client.post(reverse("create_clicked_job_posting", args=[job_posting.pk]))

    assert response.status_code == 302
    assert ClickedJobPosting.objects.count() == 0


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_create_clicked_job_posting_is_closed_to_pros(client, pro, job_posting):
    client.force_login(pro)

    response = client.post(reverse("create_clicked_job_posting", args=[job_posting.pk]))

    assert response.status_code == 404
    assert ClickedJobPosting.objects.count() == 0


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_dates_a_posting_we_updated_by_its_update(client):
    job_posting = save_job_posting(
        "Stage",
        JobPosting.Category.HIGHER_ED_INTERNSHIP,
        published_at=timezone.now() - timedelta(days=10),
    )
    # The trigger moves `updated_at` along: the row changed after its creation.
    JobPosting.objects.filter(pk=job_posting.pk).update(
        created_at=timezone.now() - timedelta(days=10)
    )

    html = client.get(INDEX_JOB_POSTINGS_URL).content.decode()

    assert "Il y a 0\xa0minute" in html
    assert "Il y a 1\xa0semaine" not in html


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_links_each_posting_to_its_page_by_its_title(client):
    """The title is the link, stretched over the card: its name is the text she sees."""
    job_posting = save_job_posting("Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP)

    html = client.get(INDEX_JOB_POSTINGS_URL).content.decode()

    assert re.search(
        rf'<h3[^>]*>\s*<a href="{show_job_posting_url(job_posting)}"[^>]*>\s*Stage\s*</a>', html
    )
    assert 'aria-label="Voir l’offre' not in html


@pytest.fixture
def cybersecurity_postings():
    now = timezone.now()
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    save_job_posting("Stage en cybersécurité", category, published_at=now - timedelta(days=5))
    save_job_posting(
        "Stage en réseaux", category, published_at=now, description="Un peu de cybersécurité"
    )
    save_job_posting("Stage en design", category, published_at=now)


def ordered_titles(response):
    return [job_posting.title for job_posting in response.context["job_postings"]]


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_searches_by_relevance_by_default(client, cybersecurity_postings):
    response = client.get(INDEX_JOB_POSTINGS_URL, {"q": "cybersécurité"})

    assert ordered_titles(response) == ["Stage en cybersécurité", "Stage en réseaux"]


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_sorts_a_search_by_date_on_request(client, cybersecurity_postings):
    response = client.get(INDEX_JOB_POSTINGS_URL, {"q": "cybersécurité", "sort": "date"})

    assert ordered_titles(response) == ["Stage en réseaux", "Stage en cybersécurité"]


@pytest.mark.django_db
@pytest.mark.parametrize("q", ["c", " c  ", "   "])
@override_switch("internships", active=True)
def test_index_job_postings_ignores_a_search_under_two_characters(client, q):
    save_job_posting("Stage en design", JobPosting.Category.HIGHER_ED_INTERNSHIP)

    response = client.get(INDEX_JOB_POSTINGS_URL, {"q": q})

    assert listed_titles(response) == {"Stage en design"}
    assert 'name="sort"' not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, invalid",
    [
        ({"q": "c"}, True),
        ({"q": " c  "}, True),
        ({"q": "ia"}, False),
        ({"q": "   "}, False),
        ({}, False),
    ],
    ids=["too_short", "too_short_once_trimmed", "long_enough", "blank", "absent"],
)
@override_switch("internships", active=True)
def test_index_job_postings_shows_an_error_under_two_characters(client, query, invalid):
    html = client.get(INDEX_JOB_POSTINGS_URL, query).content.decode()

    assert ("Saisis au moins 2 caractères" in html) == invalid
    assert ('aria-invalid="true"' in html) == invalid


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_searches_within_the_category_and_the_filters(client):
    save_job_posting("Stage web", JobPosting.Category.HIGHER_ED_INTERNSHIP)
    save_job_posting(
        "Stage web en maths", JobPosting.Category.HIGHER_ED_INTERNSHIP, domains=["mathematiques"]
    )
    save_job_posting("Alternance web", JobPosting.Category.APPRENTICESHIP)

    response = client.get(INDEX_JOB_POSTINGS_URL, {"q": "web", "domain": "mathematiques"})

    assert listed_titles(response) == {"Stage web en maths"}


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_offers_the_sort_only_once_she_searched(client):
    without_search = client.get(INDEX_JOB_POSTINGS_URL).content.decode()
    with_search = client.get(INDEX_JOB_POSTINGS_URL, {"q": "web"}).content.decode()

    assert 'name="sort"' not in without_search
    assert 'name="sort"' in with_search


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, selected",
    [({"q": "web"}, "relevance"), ({"q": "web", "sort": "date"}, "date")],
    ids=["default", "asked_for"],
)
@override_switch("internships", active=True)
def test_index_job_postings_selects_the_sort_in_use(client, query, selected):
    html = client.get(INDEX_JOB_POSTINGS_URL, query).content.decode()

    assert re.findall(r'name="sort" value="([^"]*)"\s+checked', html) == [selected]


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_shows_the_search_in_its_field(client):
    html = client.get(INDEX_JOB_POSTINGS_URL, {"q": '"web'}).content.decode()

    assert 'value="&quot;web"' in html


@pytest.mark.django_db
@override_switch("internships", active=True)
def test_index_job_postings_keeps_the_search_and_the_sort_in_the_link_to_the_next_page(
    client, twenty_one_apprenticeships
):
    response = client.get(
        INDEX_JOB_POSTINGS_URL,
        {"category": "apprenticeship", "q": "alternance", "sort": "date"},
    )

    assert (
        b'href="?category=apprenticeship&amp;q=alternance&amp;sort=date&page=2"'
        in response.content
    )


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
def test_index_events_is_never_served_from_the_browser_cache(client, salon):
    """Back or forward would otherwise show the bookmarks as they were before a toggle."""
    response = client.get(INDEX_EVENTS_URL)

    assert "no-store" in response["Cache-Control"]


@pytest.mark.django_db
def test_show_event_is_never_served_from_the_browser_cache(client, salon):
    response = client.get(reverse("show_event", args=[salon.slug]))

    assert "no-store" in response["Cache-Control"]


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


EVENTS_LISTING = f"{INDEX_EVENTS_URL}?page=2"


@pytest.mark.django_db
def test_show_event_hands_the_page_and_its_listing_to_the_save_modal(client, salon):
    show_event_url = reverse("show_event", args=[salon.slug])
    page_url = _with_way_back(show_event_url, f"{EVENTS_LISTING}#evenement-{salon.slug}")

    content = client.get(
        show_event_url, HTTP_REFERER=f"http://testserver{EVENTS_LISTING}"
    ).content.decode()

    save_modal = reverse("create_saved_event_modal", args=[salon.pk])
    assert content.count(f"{save_modal}?back={quote(page_url, safe='')}") == 2


@pytest.mark.django_db
def test_create_saved_event_modal_carries_the_way_back_it_is_given(client, salon):
    page_url = _with_way_back(reverse("show_event", args=[salon.slug]), EVENTS_LISTING)

    content = client.get(
        reverse("create_saved_event_modal", args=[salon.pk]), {"back": page_url}
    ).content.decode()

    _assert_both_ways_in_go_back_to(content, "saved_event", salon.pk, page_url)


@pytest.mark.django_db
def test_create_saved_event_modal_goes_back_to_the_listing_it_was_opened_from(client, salon):
    content = client.get(
        reverse("create_saved_event_modal", args=[salon.pk]),
        HTTP_HX_CURRENT_URL=f"http://testserver{EVENTS_LISTING}",
    ).content.decode()

    _assert_both_ways_in_go_back_to(content, "saved_event", salon.pk, EVENTS_LISTING)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("query", "current_url"),
    [({}, ""), ({"back": "https://evil.example/"}, "https://evil.example/evenements/")],
)
def test_create_saved_event_modal_goes_back_to_the_event_by_default(
    client, salon, query, current_url
):
    content = client.get(
        reverse("create_saved_event_modal", args=[salon.pk]),
        query,
        HTTP_HX_CURRENT_URL=current_url,
    ).content.decode()

    _assert_both_ways_in_go_back_to(
        content, "saved_event", salon.pk, reverse("show_event", args=[salon.slug])
    )


@pytest.mark.django_db
def test_create_saved_event_modal_ignores_an_event_awaiting_validation(client, event):
    assert client.get(reverse("create_saved_event_modal", args=[event.pk])).status_code == 404


@pytest.mark.django_db
def test_show_event_renders_the_event(client, salon):
    response = client.get(reverse("show_event", args=[salon.slug]))

    assert response.status_code == 200
    assert salon.title.encode() in response.content


@pytest.mark.django_db
def test_show_event_shows_a_pending_message_once(client, beneficiary, salon):
    response = _signed_in_on(client, beneficiary, reverse("show_event", args=[salon.slug]))

    assert response.content.decode().count("Bienvenue sur le compte") == 1


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


def _staff(email):
    return User.objects.create_user(
        username=email, email=email, first_name="Ada", last_name="Moderatrice", is_staff=True
    )


@pytest.mark.django_db
def test_show_event_lets_its_moderator_open_an_event_awaiting_validation(client, event, settings):
    event.created_by.structure_type = Pro.StructureType.ASSOCIATION
    event.created_by.save()
    settings.COALITION_ASSOCIATION_RECIPIENTS = ["staff@example.com"]
    client.force_login(_staff("staff@example.com"))

    assert client.get(reverse("show_event", args=[event.slug])).status_code == 200


@pytest.mark.django_db
def test_show_event_hides_an_event_awaiting_validation_from_another_teams_staff(
    client, event, settings
):
    event.created_by.structure_type = Pro.StructureType.ASSOCIATION
    event.created_by.save()
    settings.COALITION_ASSOCIATION_RECIPIENTS = ["staff@example.com"]
    client.force_login(_staff("other-team@example.com"))

    assert client.get(reverse("show_event", args=[event.slug])).status_code == 404


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

    assert (
        response.context["back_url"]
        == f"{INDEX_EVENTS_URL}?page=3&q=hackathon#evenement-{salon.slug}"
    )


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

    assert response.context["back_url"] == f"{reverse('index_pro_events')}#evenement-{salon.slug}"


@pytest.mark.django_db
def test_show_event_back_link_trusts_a_back_param_from_the_pro_events_page(client, salon):
    """The edit-event funnel redirects here with `?back=...` rather than a matching referer,
    since the previous page in the browser's history is the funnel itself."""
    response = client.get(
        reverse("show_event", args=[salon.slug]), {"back": reverse("index_pro_events")}
    )

    assert response.context["back_url"] == f"{reverse('index_pro_events')}#evenement-{salon.slug}"


@pytest.mark.django_db
def test_index_events_anchors_each_card_for_the_way_back(client, salon):
    content = client.get(INDEX_EVENTS_URL).content.decode()

    assert f'id="evenement-{salon.slug}"' in content


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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "domains, stacked",
    [
        ([JobPosting.Domain.DEVELOPPEMENT, JobPosting.Domain.MATHEMATIQUES], False),
        (
            [
                JobPosting.Domain.DEVELOPPEMENT,
                JobPosting.Domain.MATHEMATIQUES,
                JobPosting.Domain.ELECTRONIQUE,
            ],
            True,
        ),
    ],
)
@override_switch("internships", active=True)
def test_show_job_posting_stacks_the_domains_from_three_on(client, domains, stacked):
    category = JobPosting.Category.HIGHER_ED_INTERNSHIP
    job_posting = save_job_posting("Stage", category, domains=domains)

    html = client.get(show_job_posting_url(job_posting)).content.decode()

    assert ("autres domaines" in html) == stacked
    assert ("Réduire" in html) == stacked
