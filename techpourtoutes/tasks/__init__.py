from .create_mentor import create_mentor_task
from .create_mentoree import create_mentoree_task
from .create_upcoming_feature_notification import create_upcoming_feature_notification_task
from .delete_brevo_contact import delete_brevo_contact_task
from .flag_recommended_schools import flag_recommended_schools_task
from .flag_training_ambassador_schools import flag_training_ambassador_schools_task
from .import_carif_oref_formations import import_carif_oref_formations_task
from .import_myfuture_job_postings import import_myfuture_job_postings_task
from .import_onisep_formation_actions import import_onisep_formation_actions_task
from .import_onisep_formations import import_onisep_formations_task
from .import_onisep_schools import import_onisep_schools_task
from .notify_workshop_request import notify_workshop_request_task
from .send_beneficiary_welcome_email import send_beneficiary_welcome_email_task
from .send_event_updated_email import send_event_updated_email_task
from .send_legal_representative_authorization_proof import (
    send_legal_representative_authorization_proof_task,
)
from .subscribe_legal_representative_to_newsletter import (
    subscribe_legal_representative_to_newsletter_task,
)
from .upsert_brevo_contact import upsert_brevo_contact_task
from .upsert_manifeste_signatory import upsert_manifeste_signatory_task

__all__ = (
    "create_mentor_task",
    "create_mentoree_task",
    "delete_brevo_contact_task",
    "flag_recommended_schools_task",
    "flag_training_ambassador_schools_task",
    "import_carif_oref_formations_task",
    "import_myfuture_job_postings_task",
    "import_onisep_formation_actions_task",
    "import_onisep_formations_task",
    "import_onisep_schools_task",
    "notify_workshop_request_task",
    "send_beneficiary_welcome_email_task",
    "send_event_updated_email_task",
    "send_legal_representative_authorization_proof_task",
    "subscribe_legal_representative_to_newsletter_task",
    "upsert_brevo_contact_task",
    "create_upcoming_feature_notification_task",
    "upsert_manifeste_signatory_task",
)
