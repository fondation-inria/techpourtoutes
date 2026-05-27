from .auth_views import (
    account,
    login_email_sent,
    login_request,
    login_to_jobirl,
    login_verify,
    logout_view,
)
from .coallition_views import coallition_index, mentor_landing, mentor_success
from .legal_views import (
    accessibilite,
    conditions_generales,
    donnees_personnelles,
    mentions_legales,
    schema_pluriannuel,
)

__all__ = [
    "accessibilite",
    "account",
    "coallition_index",
    "conditions_generales",
    "donnees_personnelles",
    "login_email_sent",
    "login_request",
    "login_to_jobirl",
    "login_verify",
    "logout_view",
    "mentions_legales",
    "mentor_landing",
    "mentor_success",
    "schema_pluriannuel",
]
