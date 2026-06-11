import unicodedata


def strip_accents(text: str) -> str:
    """Drop accents so search/matching is accent-insensitive (e.g. "Lycée" -> "Lycee")."""
    return "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )
