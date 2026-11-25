import re
from itertools import batched

from techpourtoutes.models import JobPosting

# HTML tags the descriptions use to lay themselves out; everything else is dropped, its text kept.
DESCRIPTION_TAGS = {
    "p",
    "div",
    "br",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "strong",
    "b",
    "em",
    "u",
    "sup",
    "a",
}
DESCRIPTION_ATTRIBUTES = {"a": {"href"}}

TAG = re.compile(r"(<[^>]*>)")
LINE_BREAK = re.compile(r"(\S+)([ \t]*\n\s*)(?=(\S))")
SENTENCE_ENDS = ".:;!?»)…"
# Words a line never ends on unless the text was wrapped mid-sentence.
FUNCTION_WORDS = {
    "à",
    "au",
    "aux",
    "avec",
    "dans",
    "de",
    "des",
    "du",
    "en",
    "et",
    "la",
    "le",
    "les",
    "nos",
    "notre",
    "ou",
    "par",
    "pour",
    "qui",
    "que",
    "sa",
    "ses",
    "son",
    "sur",
    "un",
    "une",
    "vos",
    "votre",
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "the",
    "to",
    "with",
}

BATCH_SIZE = 1000


def city_name(city: str) -> str:
    """Title-case a city the partner spelled in capitals; keep the others as spelled, since
    `str.title` would also capitalise the `sur` and `l'` of `Aire-sur-l'Adour`."""
    return city.title() if city.isupper() else city


def with_line_breaks(description: str) -> str:
    """Show the line breaks the partner typed in the text, which a browser shows as spaces. A
    break within a sentence — before a lowercase word, after a word no line ends on — was only
    the text wrapping at a fixed width, and is left as typed. Only the text is read, never the tags
    or what separates them."""
    parts = TAG.split(description)
    parts[::2] = [LINE_BREAK.sub(_line_break, text) for text in parts[::2]]
    return "".join(parts)


def _line_break(match):
    before, gap, first_after = match.groups()
    if gap.count("\n") > 1:
        return f"{before}<br><br>"
    if _wraps(before, first_after):
        return match[0]
    return f"{before}<br>"


def _wraps(before, first_after):
    return (
        before[-1] not in SENTENCE_ENDS
        and first_after.isalnum()
        and (first_after.islower() or before.lower() in FUNCTION_WORDS or before[-1] in "'’")
    )


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
