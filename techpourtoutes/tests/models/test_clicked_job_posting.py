import pytest
from django.core.exceptions import ValidationError

from techpourtoutes.models import Beneficiary, ClickedJobPosting


@pytest.mark.django_db
def test_a_beneficiary_clicks_a_job_posting_only_once(job_posting, beneficiary):
    ClickedJobPosting(job_posting=job_posting, beneficiary=beneficiary).save()

    with pytest.raises(ValidationError):
        ClickedJobPosting(job_posting=job_posting, beneficiary=beneficiary).save()


@pytest.mark.django_db
def test_a_clicked_job_posting_is_reachable_from_both_sides(job_posting, beneficiary):
    click = ClickedJobPosting(job_posting=job_posting, beneficiary=beneficiary)
    click.save()

    assert list(beneficiary.clicked_job_postings.all()) == [job_posting]
    assert list(job_posting.clicks.all()) == [click]
    assert click.created_at is not None
    assert str(click) == "Jade PETIT – Développeuse web"


@pytest.mark.django_db
def test_toggle_marks_a_job_posting_clicked_then_takes_it_back(job_posting, beneficiary):
    assert ClickedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=beneficiary)
    assert list(beneficiary.clicked_job_postings.all()) == [job_posting]

    assert not ClickedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=beneficiary)
    assert list(beneficiary.clicked_job_postings.all()) == []


@pytest.mark.django_db
def test_toggle_leaves_another_beneficiarys_click_alone(job_posting, beneficiary):
    other = Beneficiary(
        username="lou@example.com", email="lou@example.com", first_name="Lou", last_name="Bernard"
    )
    other.save()
    ClickedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=other)

    ClickedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=beneficiary)
    ClickedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=beneficiary)

    assert list(other.clicked_job_postings.all()) == [job_posting]


@pytest.mark.django_db
def test_a_clicked_job_posting_goes_with_the_job_posting(job_posting, beneficiary):
    ClickedJobPosting(job_posting=job_posting, beneficiary=beneficiary).save()

    job_posting.delete()

    assert not ClickedJobPosting.objects.exists()
