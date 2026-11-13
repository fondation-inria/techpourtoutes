import importlib

import pytest
from django.apps import apps

from techpourtoutes.models import JobPosting

from ..views.test_beneficiary_views import save_job_posting

migration = importlib.import_module("techpourtoutes.migrations.0077_jobposting_pmsmp_and_pfmp")

pytestmark = pytest.mark.django_db

Category = JobPosting.Category


def test_the_first_jobs_of_myfuture_become_immersions():
    save_job_posting("PMSMP", Category.FIRST_JOB, source=JobPosting.Source.MYFUTURE)

    migration.set_pmsmp_contract_type(apps, None)

    assert JobPosting.objects.get().contract_type == JobPosting.ContractType.PMSMP


@pytest.mark.parametrize(
    ("source", "category", "contract_type"),
    [
        (JobPosting.Source.APEC, Category.FIRST_JOB, JobPosting.ContractType.CDI),
        (JobPosting.Source.MYFUTURE, Category.TROISIEME_INTERNSHIP, ""),
    ],
)
def test_the_other_postings_keep_their_contract_type(source, category, contract_type):
    save_job_posting("Offre", category, source=source, contract_type=contract_type)

    migration.set_pmsmp_contract_type(apps, None)

    assert JobPosting.objects.get().contract_type == contract_type
