import pytest
from django.core.exceptions import ValidationError

from techpourtoutes.models import JobPosting

from ..views.test_beneficiary_views import save_job_posting


@pytest.mark.django_db
def test_job_posting_rejects_a_domain_outside_the_choices():
    with pytest.raises(ValidationError, match="domains"):
        save_job_posting(
            "Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP, domains=["Développement web"]
        )
