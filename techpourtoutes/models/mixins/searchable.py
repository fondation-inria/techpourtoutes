from django.contrib.postgres.search import SearchRank
from django.db import models

from techpourtoutes.utils.full_text_search import search_query


class SearchableQuerySetMixin:
    """For a model holding a `search_vector` column built by `search_vector()`."""

    def search(self, terms):
        terms = terms.replace("\x00", "")
        query = search_query(terms)
        return self.filter(self._search_match(terms, query)).annotate(
            relevance=SearchRank(models.F("search_vector"), query)
        )

    def _search_match(self, terms, query):
        return models.Q(search_vector=query)
