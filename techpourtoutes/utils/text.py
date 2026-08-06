import unicodedata


def strip_accents(text: str) -> str:
    """Drop accents so search/matching is accent-insensitive (e.g. "Lycée" -> "Lycee")."""
    return "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )


def mask_email(email: str) -> str:
    """Partially hide a local part for display (e.g. "quentin@inria.fr" -> "q***n@inria.fr")."""
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked = local[:1] + "***"
    else:
        masked = f"{local[0]}***{local[-1]}"
    return f"{masked}@{domain}"
