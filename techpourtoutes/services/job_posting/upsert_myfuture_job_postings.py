import nh3
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from techpourtoutes.models import JobPosting
from techpourtoutes.services.base import BaseService
from techpourtoutes.utils.myfuture import SUB_DOMAINS

# Lowercased, because MyFuture spells some of them several ways (`PMSMP`, `3einternship`).
# An offer of several types lands in the first of them listed here.
# `miniInternship`, `visit` and `highSchoolInternship` fit no category and are left out: the last
# is MyFuture's long internship in a lycée pro (PFMP), not the seconde one.
CATEGORIES = {
    "3einternship": JobPosting.Category.TROISIEME_INTERNSHIP,
    "studentinternship": JobPosting.Category.HIGHER_ED_INTERNSHIP,
    "apprenticeship": JobPosting.Category.APPRENTICESHIP,
    "pmsmp": JobPosting.Category.FIRST_JOB,
}

# HTML tags the descriptions use to lay themselves out; everything else is dropped, its text kept.
DESCRIPTION_TAGS = {"p", "br", "h2", "h3", "h4", "ul", "ol", "li", "strong", "em", "u", "sup", "a"}
DESCRIPTION_ATTRIBUTES = {"a": {"href"}}

MAPPED_FIELDS = [
    "title",
    "company_name",
    "description",
    "postal_code",
    "cog_code",
    "city",
    "domains",
    "company_logo",
    "category",
    "contract_type",
    "published_at",
    "source_updated_at",
    "url",
]


class UpsertMyFutureJobPostings(BaseService):
    """Mirror MyFuture: what it lists is created or updated, what it no longer lists is deleted.

    An offer is skipped when it fits none of our categories, has no city to show, or lists only
    periods that have passed.
    """

    def perform(self, *, records) -> None:
        postings = [
            self._posting(record)
            for record in records
            if _category(record) and record["address"].get("city") and not _expired(record)
        ]
        JobPosting.objects.bulk_create(
            postings,
            update_conflicts=True,
            unique_fields=["source", "external_id"],
            update_fields=MAPPED_FIELDS,
            batch_size=1000,
        )
        JobPosting.all_objects.filter(source=JobPosting.Source.MYFUTURE).exclude(
            external_id__in=[posting.external_id for posting in postings]
        ).delete()

    def _posting(self, record):
        address = record["address"]
        category = _category(record)
        return JobPosting(
            source=JobPosting.Source.MYFUTURE,
            external_id=record["_id"],
            title=record["title"],
            company_name=record["owner_name"],
            description=nh3.clean(
                record["description"],
                tags=DESCRIPTION_TAGS,
                attributes=DESCRIPTION_ATTRIBUTES,
            ),
            postal_code=address.get("postalCode") or "",
            cog_code=address.get("inseeCode") or "",
            city=address["city"],
            domains=[SUB_DOMAINS[key] for key in record["subDomainKeys"] if key in SUB_DOMAINS],
            company_logo=record["owner_logo"] or "",
            category=category,
            contract_type=(
                JobPosting.ContractType.APPRENTICESHIP
                if category == JobPosting.Category.APPRENTICESHIP
                else ""
            ),
            published_at=parse_datetime(record["createdAt"]),
            source_updated_at=parse_datetime(record["updatedAt"]),
            url=record["canonicalUrl"],
        )


def _category(record):
    types = {internship_type.lower() for internship_type in record["internshipTypes"]}
    return next((category for type_, category in CATEGORIES.items() if type_ in types), None)


def _expired(record) -> bool:
    """Most offers list no period at all: those never expire."""
    periods = record["periods"]
    return bool(periods) and all(
        parse_datetime(period["to"]) < timezone.now() for period in periods
    )
