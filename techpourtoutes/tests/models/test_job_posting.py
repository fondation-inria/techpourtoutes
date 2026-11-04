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


def test_job_posting_domains_are_the_normalized_list():
    assert JobPosting.Domain.labels == [
        "Électronique",
        "Électrotechnique",
        "Télécommunications",
        "Bases de données",
        "Développement - programmation - logiciel",
        "Informatique de gestion",
        "Informatique",
        "Informatique industrielle",
        "Informatique pour la recherche",
        "Systèmes et réseaux",
        "Mathématiques",
        "Sciences de l’univers",
        "Exploitation, maintenance informatique",
        "Maîtrise d’ouvrage et fonctionnel",
        "Création",
        "Conception, recherche",
        "Direction recherche et développement",
        "Projets scientifiques et techniques",
        "Test, essai, validation, expertise",
    ]
