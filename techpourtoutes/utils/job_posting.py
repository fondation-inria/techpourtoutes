from itertools import batched

from techpourtoutes.models import JobPosting

# HTML tags the descriptions use to lay themselves out; everything else is dropped, its text kept.
DESCRIPTION_TAGS = {"p", "br", "h2", "h3", "h4", "ul", "ol", "li", "strong", "em", "u", "sup", "a"}
DESCRIPTION_ATTRIBUTES = {"a": {"href"}}

BATCH_SIZE = 1000


def city_name(city: str) -> str:
    """Title-case a city the partner spelled in capitals; keep the others as spelled, since
    `str.title` would also capitalise the `sur` and `l'` of `Aire-sur-l'Adour`."""
    return city.title() if city.isupper() else city


def upsert_in_batches(postings, *, update_fields) -> list[str]:
    """Create or update the postings a batch at a time, so that only one batch is ever held in
    memory, and hand back their ids. The caller makes it all or nothing."""
    external_ids = []
    for batch in batched(postings, BATCH_SIZE):
        JobPosting.objects.bulk_create(
            batch,
            update_conflicts=True,
            unique_fields=["source", "external_id"],
            update_fields=update_fields,
        )
        external_ids += [posting.external_id for posting in batch]
    return external_ids
