import operator
import re
from functools import reduce

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import models

SEARCH_CONFIG = "french_unaccent"
MASCULINE_OF_FEMININE = (("euse", "eur"), ("trice", "teur"), ("cheffe", "chef"), ("[ée]e", "é"))


def search_vector(*weighted_fields):
    """The expression of a `search_vector` column over `(field, weight)` pairs, every word in
    the masculine so that a search in either gender finds both."""
    return reduce(
        operator.add,
        (
            SearchVector(_masculine_text(field), weight=weight, config=SEARCH_CONFIG)
            for field, weight in weighted_fields
        ),
    )


class SearchableQuerySetMixin:
    """For a model holding a `search_vector` column built by `search_vector()`."""

    def search(self, terms):
        query = SearchQuery(
            " & ".join(
                _any_spelling(_masculine(word))
                for word in terms.replace("\x00", "").lower().split()
            ),
            search_type="raw",
            config=SEARCH_CONFIG,
        )
        return self.filter(search_vector=query).annotate(
            relevance=SearchRank(models.F("search_vector"), query)
        )


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


def _masculine_text(field):
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
