import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.cookie import CookieStorage
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse

from techpourtoutes.decorators import beneficiary_required, pro_required


@pro_required
def pro_view(request):
    return HttpResponse("ok")


@beneficiary_required
def beneficiary_view(request):
    return HttpResponse("ok")


def call(view, user):
    request = RequestFactory().get("/une-page/")
    request.user = user
    request._messages = CookieStorage(request)
    return request, view(request)


@pytest.mark.django_db
def test_an_anonymous_visitor_is_sent_to_the_login_page():
    _, response = call(pro_view, AnonymousUser())

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]


@pytest.mark.django_db
def test_a_beneficiary_is_turned_away_from_a_pro_page(beneficiary):
    request, response = call(pro_view, beneficiary)

    assert response.status_code == 302
    assert response["Location"] == reverse("account")
    assert "réservée aux professionnelles" in str(list(request._messages)[0])


@pytest.mark.django_db
def test_a_pro_is_turned_away_from_a_beneficiary_page(pro):
    request, response = call(beneficiary_view, pro)

    assert response.status_code == 302
    assert response["Location"] == reverse("account")
    assert "réservée aux bénéficiaires" in str(list(request._messages)[0])


@pytest.mark.django_db
def test_each_role_reaches_its_own_page(pro, beneficiary):
    assert call(pro_view, pro)[1].status_code == 200
    assert call(beneficiary_view, beneficiary)[1].status_code == 200
