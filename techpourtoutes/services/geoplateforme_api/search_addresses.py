from .base_service import GeoplateformeApiBaseService


class SearchAddresses(GeoplateformeApiBaseService):
    """The addresses matching what the user typed, flattened onto the `Event` column names."""

    def perform(self, *, query: str) -> None:
        self.addresses = []
        if not query.strip():
            return
        payload = self.request(method="search_addresses", query=query)
        self.addresses = [
            address
            for feature in payload.get("features", [])
            if (address := self._address(feature)) is not None
        ]

    def _address(self, feature):
        """No coordinates means nothing worth storing: such a hit could never be approved."""
        coordinates = feature.get("geometry", {}).get("coordinates")
        if not coordinates:
            return None
        properties = feature.get("properties", {})
        return {
            "ban_id": properties.get("id", ""),
            "label": properties.get("label", ""),
            "address": properties.get("name", ""),
            "postal_code": properties.get("postcode", ""),
            "city": properties.get("city", ""),
            "cog_code": properties.get("citycode", ""),
            "longitude": coordinates[0],
            "latitude": coordinates[1],
        }
