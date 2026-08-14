import pytest
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_workshop_request_links_to_pro_and_stores_data(pro):
    from techpourtoutes.models import WorkshopRequest

    req = WorkshopRequest(pro=pro, type="future_of_tech", remark="Top")
    req.save()

    assert list(pro.workshop_requests.all()) == [req]
    assert req.type == "future_of_tech"
    assert req.remark == "Top"
    assert req.created_at is not None


@pytest.mark.django_db
def test_workshop_request_rejects_invalid_type(pro):
    from techpourtoutes.models import WorkshopRequest

    with pytest.raises(ValidationError):
        WorkshopRequest(pro=pro, type="not-a-real-atelier").save()


@pytest.mark.django_db
def test_workshop_request_query_pros_by_type(pro):
    from techpourtoutes.models import Pro, WorkshopRequest

    WorkshopRequest(pro=pro, type="future_of_tech").save()

    matching = Pro.objects.filter(workshop_requests__type="future_of_tech")
    assert pro in matching
