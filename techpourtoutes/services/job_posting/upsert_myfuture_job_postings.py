import nh3
from django.utils.dateparse import parse_datetime

from techpourtoutes.models import JobPosting
from techpourtoutes.services.base import BaseService
from techpourtoutes.utils.myfuture import SUB_DOMAINS

# Lowercased, because MyFuture spells some of them both ways (`PMSMP`, `3einternship`).
# `miniInternship` and `visit` fit no category and are left out.
CATEGORIES = {
    "3einternship": JobPosting.Category.TROISIEME_INTERNSHIP,
    "highschoolinternship": JobPosting.Category.SECONDE_INTERNSHIP,
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
    "categories",
    "contract_type",
    "published_at",
    "source_updated_at",
    "url",
]


class UpsertMyFutureJobPostings(BaseService):
    """Mirror MyFuture: what it lists is created or updated, what it no longer lists is deleted.

    An offer is skipped when it fits none of our categories, or has no city to show.
    """

    def perform(self, *, records) -> None:
        postings = [
            self._posting(record)
            for record in records
            if _categories(record) and record["address"].get("city")
        ]
        JobPosting.objects.bulk_create(
            postings,
            update_conflicts=True,
            unique_fields=["source", "external_id"],
            update_fields=MAPPED_FIELDS,
            batch_size=1000,
        )
        JobPosting.objects.filter(source=JobPosting.Source.MYFUTURE).exclude(
            external_id__in=[posting.external_id for posting in postings]
        ).delete()

    def _posting(self, record):
        address = record["address"]
        categories = _categories(record)
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
            categories=categories,
            contract_type=(
                JobPosting.ContractType.APPRENTICESHIP
                if JobPosting.Category.APPRENTICESHIP in categories
                else ""
            ),
            published_at=parse_datetime(record["createdAt"]),
            source_updated_at=parse_datetime(record["updatedAt"]),
            url=record["canonicalUrl"],
        )


def _categories(record) -> list:
    types = (internship_type.lower() for internship_type in record["internshipTypes"])
    return list(dict.fromkeys(CATEGORIES[type_] for type_ in types if type_ in CATEGORIES))
