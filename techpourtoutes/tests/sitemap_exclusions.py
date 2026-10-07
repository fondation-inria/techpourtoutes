from techpourtoutes import urls_beneficiary, urls_coalition, urls_common

# Argument-free routes that no sitemap lists — neither the XML sitemap (for search engines)
# nor the HTML sitemap (the plan du site): none of them is a destination. What each sitemap
# excludes on top of these is decided, and explained, next to its own guard test.
NEVER_LISTED_URL_NAMES = {
    # HTMX partials
    "search_schools",
    "search_formations",
    "search_addresses",
    # Auth ("Mon compte" is the entry point)
    "login_request",
    "login_code",
    "login_to_jobirl",
    "destroy_session",
    # Signed-in area, reached from "Mon compte"
    "show_user",
    "show_user_info",
    "edit_user",
    "update_user",
    "update_user_communication",
    "show_user_email",
    "edit_user_email",
    "create_user_email_change",
    "create_user_email_code",
    "show_user_email_verification",
    "update_user_email",
    "show_beneficiary_legal_rep",
    "edit_beneficiary_legal_rep",
    "update_beneficiary_legal_rep",
    "new_beneficiary_training_experience",
    "create_beneficiary_training_experience",
    "destroy_user_modal",
    "destroy_user",
    "index_pro_events",
    "index_beneficiary_events",
    "new_event",
    "new_training_ambassador_request",
    "create_training_ambassador_request",
    # Form submission endpoints (their GET page is the one listed)
    "create_mentor",
    "create_work_ambassador",
    "create_training_ambassador",
    "create_sponsor",
    "create_workshop_request",
    "create_manifeste_signature",
    "create_upcoming_feature_notification",
    "create_event",
    "update_event",
    # Funnel steps (not entry points)
    "inscription_funnel",
    "mentoring_funnel",
    "coalition_welcome",
    "show_manifeste_signature",
    # Redirects
    "a_propos",
}


def argument_free_url_names():
    return {
        pattern.name
        for module in (urls_beneficiary, urls_coalition, urls_common)
        for pattern in module.urlpatterns
        if pattern.name and not pattern.pattern.converters
    }
