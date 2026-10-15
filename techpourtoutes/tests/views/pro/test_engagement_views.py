from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

from techpourtoutes.models import Pro
from techpourtoutes.services.base import ErrorKind

REGISTER = "techpourtoutes.services.pro.create_mentor.RegisterUserOnJobirl"

pytestmark = pytest.mark.django_db


@pytest.fixture
def complete_pro(pro):
    pro.structure_type = Pro.StructureType.COMPANY
    pro.save()
    return pro


def _new(engagement):
    return reverse("new_pro_engagement", args=[engagement])


def _create(engagement):
    return reverse("create_pro_engagement", args=[engagement])


def _with_engagements(pro, *engagements):
    pro.engagements = list(engagements)
    pro.save()


# ------------------- new_pro_engagement -------------------


def test_new_pro_engagement_knows_no_other_engagement(client, pro):
    client.force_login(pro)
    assert client.get(_new("events")).status_code == 404


def test_new_pro_engagement_signs_up_a_visitor_with_it(client):
    response = client.get(_new("sponsor"))
    assert response["Location"] == f"{reverse('new_pro_inscription_funnel')}?engagement=sponsor"


def test_new_pro_engagement_is_only_for_pros(client, beneficiary):
    client.force_login(beneficiary)
    assert client.get(_new("sponsor")).status_code == 404


def test_new_pro_engagement_only_asks_what_she_has_not_given(client, pro):
    client.force_login(pro)

    response = client.get(_new("sponsor")).content.decode()

    assert 'id="id_structure_type"' in response
    for name in ("structure_name", "job_title", "phone", "postal_code"):
        assert f'id="id_{name}"' not in response
    assert f'hx-post="{_create("sponsor")}"' in response


@pytest.mark.parametrize(
    "engagement,field",
    [("training_ambassador", "id_school_label"), ("workshops", "id_workshop-school_label")],
)
def test_new_pro_engagement_shows_the_screen_of_her_engagement(
    client, complete_pro, engagement, field
):
    client.force_login(complete_pro)
    assert f'id="{field}"' in client.get(_new(engagement)).content.decode()


# Her button posts at once what needs nothing more: the page is only reached by its URL.
def test_new_pro_engagement_sends_to_the_account_what_needs_nothing_more(client, complete_pro):
    client.force_login(complete_pro)
    response = client.get(_new("sponsor"))
    assert response["Location"] == reverse("show_account")


# ------------------- create_pro_engagement -------------------


def test_create_pro_engagement_adds_it_and_goes_back_to_the_account(client, pro):
    client.force_login(pro)

    response = client.post(_create("sponsor"), {"structure_type": "company"})

    assert response["HX-Redirect"] == reverse("show_account")
    pro.refresh_from_db()
    assert pro.engagements == ["sponsor"]
    assert pro.structure_type == "company"
    assert "bien été ajouté" in client.get(reverse("show_account")).content.decode()


def test_create_pro_engagement_adds_what_needs_nothing_more(client, complete_pro):
    client.force_login(complete_pro)

    client.post(_create("sponsor"))

    complete_pro.refresh_from_db()
    assert complete_pro.engagements == ["sponsor"]


def test_create_pro_engagement_shows_the_screen_again_while_invalid(client, pro):
    client.force_login(pro)

    response = client.post(_create("sponsor"), {"structure_type": ""})

    assert response.status_code == 200
    assert 'id="id_structure_type"' in response.content.decode()
    pro.refresh_from_db()
    assert pro.engagements == []


def test_create_pro_engagement_goes_back_to_the_account_once_refused(client, complete_pro):
    _with_engagements(complete_pro, "sponsor")
    client.force_login(complete_pro)

    response = client.post(_create("sponsor"))

    assert response["HX-Redirect"] == reverse("show_account")
    complete_pro.refresh_from_db()
    assert complete_pro.engagements == ["sponsor"]
    assert "déjà pris cet engagement" in client.get(reverse("show_account")).content.decode()


def test_create_pro_engagement_tells_why_jobirl_refused_the_mentor(client, complete_pro):
    client.force_login(complete_pro)
    refused = MagicMock(
        success=False,
        failure=True,
        errors=["EMAIL ALREADY EXISTS"],
        failed_with_transient_error=False,
        error_kind=ErrorKind.PERMANENT,
    )

    with patch(REGISTER, return_value=refused):
        response = client.post(_create("mentor"))

    assert response["HX-Redirect"] == reverse("show_account")
    assert "EMAIL ALREADY EXISTS" in client.get(reverse("show_account")).content.decode()


# ------------------- the page she came from -------------------

_FROM = "http://testserver/coalition/"


def test_new_pro_engagement_remembers_the_page_she_came_from(client, pro):
    client.force_login(pro)

    response = client.get(_new("sponsor"), HTTP_REFERER=_FROM).content.decode()

    assert (
        f'hx-post="{_create("sponsor")}?next=http%3A%2F%2Ftestserver%2Fcoalition%2F"' in response
    )


def test_new_pro_engagement_forgets_a_page_from_another_site(client, pro):
    client.force_login(pro)

    response = client.get(_new("sponsor"), HTTP_REFERER="https://evil.example/").content.decode()

    assert "evil.example" not in response


def test_create_pro_engagement_goes_back_to_the_page_she_came_from_once_refused(
    client, complete_pro
):
    _with_engagements(complete_pro, "sponsor")
    client.force_login(complete_pro)

    response = client.post(f"{_create('sponsor')}?next={_FROM}")

    assert response["HX-Redirect"] == _FROM


def test_create_pro_engagement_never_sends_her_to_another_site(client, complete_pro):
    _with_engagements(complete_pro, "sponsor")
    client.force_login(complete_pro)

    response = client.post(f"{_create('sponsor')}?next=https://evil.example/")

    assert response["HX-Redirect"] == reverse("show_account")
