import importlib

import pytest
from django.apps import apps

from techpourtoutes.models import JobPosting

from ..views.test_beneficiary_views import save_job_posting

migration = importlib.import_module(
    "techpourtoutes.migrations.0079_jobposting_without_pmsmp_and_electrotechnique"
)

pytestmark = pytest.mark.django_db

Category = JobPosting.Category
Domain = JobPosting.Domain


def save_myfuture_job_posting(title, category=Category.TROISIEME_INTERNSHIP, **columns):
    """Saved valid, then given the values the model no longer accepts."""
    job_posting = save_job_posting(title, category, source=JobPosting.Source.MYFUTURE)
    JobPosting.objects.filter(pk=job_posting.pk).update(**columns)


def test_the_immersions_are_deleted():
    save_myfuture_job_posting("PMSMP", Category.FIRST_JOB, contract_type="pmsmp")
    save_job_posting("CDI", Category.FIRST_JOB, contract_type=JobPosting.ContractType.CDI)

    migration.remove_pmsmp_and_electrotechnique(apps, None)

    assert list(JobPosting.objects.values_list("title", flat=True)) == ["CDI"]


def test_the_postings_only_in_electrotechnique_are_deleted():
    save_myfuture_job_posting("Électrotechnique", domains=["electrotechnique"])

    migration.remove_pmsmp_and_electrotechnique(apps, None)

    assert not JobPosting.objects.exists()


def test_the_postings_also_in_another_domain_only_lose_electrotechnique():
    save_myfuture_job_posting(
        "Électronique", domains=["electrotechnique", Domain.ELECTRONIQUE, Domain.MATHEMATIQUES]
    )

    migration.remove_pmsmp_and_electrotechnique(apps, None)

    assert JobPosting.objects.get().domains == [Domain.ELECTRONIQUE, Domain.MATHEMATIQUES]
