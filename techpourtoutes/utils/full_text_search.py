import re

from django.contrib.postgres.search import SearchQuery
from django.db import models

SEARCH_CONFIG = "french_unaccent"
MASCULINE_OF_FEMININE = (("euse", "eur"), ("trice", "teur"), ("cheffe", "chef"), ("[ée]e", "é"))


def search_query(terms: str) -> SearchQuery:
    """Every word, in the masculine, as the start of a word."""
    return SearchQuery(
        " & ".join(_any_spelling(_masculine(word)) for word in terms.lower().split()),
        search_type="raw",
        config=SEARCH_CONFIG,
    )


def masculine_text(field: str) -> models.Func:
    """The field in the masculine, so that a search finds either form."""
    text = models.F(field)
    for feminine, masculine in MASCULINE_OF_FEMININE:
        text = models.Func(
            text,
            models.Value(rf"{feminine}(s?)\M"),
            models.Value(rf"{masculine}\1"),
            models.Value("gi"),
            function="regexp_replace",
            output_field=models.TextField(),
        )
    return text


def _masculine(word):
    for feminine, masculine in MASCULINE_OF_FEMININE:
        word = re.sub(rf"{feminine}(s?)\b", rf"{masculine}\1", word)
    return word


def _any_spelling(word):
    """Matches "node.js" as typed, "nodejs" and "node js", but not "node" and "js" far apart."""
    parts = re.findall(r"\w+", word)
    if len(parts) < 2:
        return _prefix(word)
    spellings = [_prefix(word), _prefix("".join(parts))]
    if all(len(part) > 1 for part in parts):
        spellings.append(" <-> ".join(_prefix(part) for part in parts))
    return "(" + " | ".join(spellings) + ")"


def _prefix(word):
    return "'" + word.replace("\\", "\\\\").replace("'", "''") + "':*"
