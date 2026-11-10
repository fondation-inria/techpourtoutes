import nh3
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from techpourtoutes.models import JobPosting
from techpourtoutes.services.base import BaseService
from techpourtoutes.utils.job_posting import (
    DESCRIPTION_ATTRIBUTES,
    DESCRIPTION_TAGS,
    city_name,
    upsert_in_batches,
)
from techpourtoutes.utils.myfuture import SUB_DOMAINS
from techpourtoutes.utils.naf import naf_label
from techpourtoutes.utils.territories import department_code

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

MAPPED_FIELDS = [
    "title",
    "company_name",
    "description",
    "postal_code",
    "cog_code",
    "department_code",
    "city",
    "street",
    "domains",
    "company_logo",
    "category",
    "contract_type",
    "sector",
    "starts_on",
    "ends_on",
    "published_at",
    "source_updated_at",
    "url",
]


class UpsertMyFutureJobPostings(BaseService):
    """Mirror MyFuture: what it lists is created or updated, what it no longer lists is deleted.

    An offer is skipped when it fits none of our categories, has no city to show, or lists only
    periods that have passed.
    """

    @transaction.atomic
    def perform(self, *, records) -> None:
        postings = (
            self._posting(record)
            for record in records
            if _category(record) and record["address"].get("city") and not _expired(record)
        )
        kept = upsert_in_batches(postings, update_fields=MAPPED_FIELDS)
        JobPosting.all_objects.filter(source=JobPosting.Source.MYFUTURE).exclude(
            external_id__in=kept
        ).delete()

    def _posting(self, record):
        address = record["address"]
        category = _category(record)
        postal_code = address.get("postalCode") or ""
        cog_code = address.get("inseeCode") or ""
        period = _next_period(record)
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
            postal_code=postal_code,
            cog_code=cog_code,
            department_code=department_code(cog_code, postal_code),
            city=city_name(address["city"]),
            # Some streets are spaced with no-break spaces, tabs or doubled spaces.
            street=" ".join((address.get("street") or "").split()),
            domains=[SUB_DOMAINS[key] for key in record["subDomainKeys"] if key in SUB_DOMAINS],
            company_logo=record["owner_logo"] or "",
            category=category,
            contract_type=(
                JobPosting.ContractType.APPRENTICESHIP
                if category == JobPosting.Category.APPRENTICESHIP
                else ""
            ),
            sector=naf_label(record.get("nafCode")),
            starts_on=period and _local_date(period["from"]),
            ends_on=period and _local_date(period["to"]),
            published_at=parse_datetime(record["createdAt"]),
            source_updated_at=parse_datetime(record["updatedAt"]),
            url=record["canonicalUrl"],
        )


def _category(record):
    types = {internship_type.lower() for internship_type in record["internshipTypes"]}
    return next((category for type_, category in CATEGORIES.items() if type_ in types), None)


def _next_period(record):
    """The earliest period not over yet: an offer often lists several."""
    upcoming = [
        period for period in record["periods"] if parse_datetime(period["to"]) >= timezone.now()
    ]
    return min(upcoming, key=lambda period: parse_datetime(period["from"]), default=None)


def _local_date(timestamp):
    return timezone.localdate(parse_datetime(timestamp))


def _expired(record) -> bool:
    """Most offers list no period at all: those never expire."""
    periods = record["periods"]
    return bool(periods) and all(
        parse_datetime(period["to"]) < timezone.now() for period in periods
    )
