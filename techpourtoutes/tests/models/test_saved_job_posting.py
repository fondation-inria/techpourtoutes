import pytest
from django.core.exceptions import ValidationError

from techpourtoutes.models import Beneficiary, SavedJobPosting


@pytest.mark.django_db
def test_a_beneficiary_saves_a_job_posting_only_once(job_posting, beneficiary):
    SavedJobPosting(job_posting=job_posting, beneficiary=beneficiary).save()

    with pytest.raises(ValidationError):
        SavedJobPosting(job_posting=job_posting, beneficiary=beneficiary).save()


@pytest.mark.django_db
def test_a_saved_job_posting_is_reachable_from_both_sides(job_posting, beneficiary):
    save = SavedJobPosting(job_posting=job_posting, beneficiary=beneficiary)
    save.save()

    assert list(beneficiary.saved_job_postings.all()) == [job_posting]
    assert list(job_posting.saves.all()) == [save]
    assert save.created_at is not None
    assert str(save) == "Jade PETIT – Développeuse web"


@pytest.mark.django_db
def test_toggle_puts_a_job_posting_aside_then_takes_it_back_out(job_posting, beneficiary):
    assert SavedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=beneficiary)
    assert list(beneficiary.saved_job_postings.all()) == [job_posting]

    assert not SavedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=beneficiary)
    assert list(beneficiary.saved_job_postings.all()) == []


@pytest.mark.django_db
def test_toggle_leaves_another_beneficiarys_save_alone(job_posting, beneficiary):
    other = Beneficiary(
        username="lou@example.com", email="lou@example.com", first_name="Lou", last_name="Bernard"
    )
    other.save()
    SavedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=other)

    SavedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=beneficiary)
    SavedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=beneficiary)

    assert list(other.saved_job_postings.all()) == [job_posting]


@pytest.mark.django_db
def test_a_saved_job_posting_goes_with_the_job_posting(job_posting, beneficiary):
    SavedJobPosting.objects.toggle(job_posting=job_posting, beneficiary=beneficiary)

    job_posting.delete()

    assert not SavedJobPosting.objects.exists()
