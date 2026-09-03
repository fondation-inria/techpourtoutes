from .base_service import GeoplateformeApiBaseService

# The API answers 400 below this, and the first keystrokes are always below it.
MIN_QUERY_LENGTH = 3

# The API's maximum, and the dropdown's: there is no offset parameter to page beyond it, so
# the whole list arrives at once and is scrolled locally.
RESULT_COUNT = 50

# A street the user actually typed scores 0.97 or more. A query naming a POI and its city —
# "station f paris" — never lifts the best street above 0.70, because what matches are the
# nameless service roads of that city. Anywhere in the band between the two separates them.
REAL_MATCH_SCORE = 0.9


class SearchAddresses(GeoplateformeApiBaseService):
    """The places matching what the user typed, flattened onto the `Event` column names.

    A street hit fills the address columns; a POI hit fills `poi_name` and leaves them empty
    — BD TOPO and the BAN share no key, so a named place cannot be resolved to its address.

    The two indexes are asked separately: asked together they come back as one ranked list, and
    a POI query ranks every street of the city above the POI, whatever the limit. Their scores
    are not comparable either, so the two are concatenated, never interleaved — whichever kind
    answers the query best comes first.
    """

    def perform(self, *, query: str) -> None:
        self.addresses = []
        if len(query.strip()) < MIN_QUERY_LENGTH:
            return
        streets = self._search(query, index="address")
        pois = self._search(query, index="poi")
        leading, trailing = (
            (streets, pois) if self._holds_a_real_match(streets) else (pois, streets)
        )
        self.addresses = [hit for _, hit in leading + trailing][:RESULT_COUNT]

    def _holds_a_real_match(self, streets):
        """The API returns each index score-sorted, so only the first one is worth looking at."""
        return bool(streets) and streets[0][0] >= REAL_MATCH_SCORE

    def _search(self, query, *, index):
        payload = self.request(
            method="search_addresses", query=query, index=index, limit=RESULT_COUNT
        )
        return [
            scored
            for feature in payload.get("features", [])
            if (scored := self._scored_hit(feature)) is not None
        ]

    def _scored_hit(self, feature):
        """No coordinates means nothing worth storing: such a hit could never be approved."""
        coordinates = feature.get("geometry", {}).get("coordinates")
        if not coordinates:
            return None
        properties = feature.get("properties", {})
        mapper = self._poi if properties.get("_type") == "poi" else self._address
        hit = mapper(properties) | {"longitude": coordinates[0], "latitude": coordinates[1]}
        return properties.get("score") or 0, hit

    def _address(self, properties):
        return {
            "ban_id": properties.get("id", ""),
            "label": properties.get("label", ""),
            "poi_name": "",
            "address": properties.get("name", ""),
            "postal_code": properties.get("postcode", ""),
            "city": properties.get("city", ""),
            "cog_code": properties.get("citycode", ""),
        }

    def _poi(self, properties):
        """The POI index answers with arrays, most specific first: a site can straddle several
        communes, and a Paris hit carries both the arrondissement and the city."""
        name = properties.get("toponym", "")
        city = self._first(properties, "city")
        return {
            "ban_id": "",
            "label": ", ".join(filter(None, [name, city])),
            "poi_name": name,
            "address": "",
            "postal_code": self._first(properties, "postcode"),
            "city": city,
            "cog_code": self._first(properties, "citycode"),
        }

    def _first(self, properties, key):
        values = properties.get(key) or []
        return values[0] if values else ""
