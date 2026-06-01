from .auth_views import (
    account,
    account_edit,
    account_info,
    login_email_sent,
    login_request,
    login_to_jobirl,
    login_verify,
    logout_view,
)
from .coalition_views import (
    coalition_index,
    coalition_welcome,
    internships_landing,
    mentor_landing,
    work_ambassador_landing,
)
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
    "account_edit",
    "account_info",
    "coalition_index",
    "conditions_generales",
    "donnees_personnelles",
    "internships_landing",
    "login_email_sent",
    "login_request",
    "login_to_jobirl",
    "login_verify",
    "logout_view",
    "mentions_legales",
    "mentor_landing",
    "coalition_welcome",
    "schema_pluriannuel",
    "work_ambassador_landing",
]
