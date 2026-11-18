import operator
from functools import reduce

from django.contrib.postgres.search import SearchRank, SearchVector
from django.db import models

from techpourtoutes.utils.full_text_search import SEARCH_CONFIG, masculine_text, search_query


def search_vector(*weighted_fields):
    """The expression of a `search_vector` column over `(field, weight)` pairs, every word in
    the masculine so that a search in either gender finds both."""
    return reduce(
        operator.add,
        (
            SearchVector(masculine_text(field), weight=weight, config=SEARCH_CONFIG)
            for field, weight in weighted_fields
        ),
    )


class SearchableQuerySetMixin:
    """For a model holding a `search_vector` column built by `search_vector()`."""

    def search(self, terms):
        query = search_query(terms.replace("\x00", ""))
        return self.filter(search_vector=query).annotate(
            relevance=SearchRank(models.F("search_vector"), query)
        )
