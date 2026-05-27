from datetime import date, datetime

from django.conf import settings
from phonenumber_field.phonenumber import PhoneNumber

FIELD_TO_BREVO_ATTR = {
    "email": "EMAIL",
    "first_name": "PRENOM",
    "last_name": "NOM",
    "phone": "SMS",
    "civility": "CIVILITE",
    "job_title": "POSTE",
    "professional_situation": "SITUATION_PRO",
    "structure_name": "STRUCTURE",
    "postal_code": "CODE_POSTAL",
}

USER_FIELDS = ["email", "first_name", "last_name"]

MENTOR_FIELDS = USER_FIELDS + [
    "phone",
    "civility",
    "job_title",
    "professional_situation",
    "structure_name",
    "postal_code",
]


def _serialize(value):
    if value is None:
        return None
    if isinstance(value, PhoneNumber):
        return value.as_e164
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _attributes_from(instance, fields: list[str]) -> dict:
    return {FIELD_TO_BREVO_ATTR[f]: _serialize(getattr(instance, f)) for f in fields}


def brevo_attributes_for(instance) -> dict | None:
    if instance.__class__.__name__ == "Mentor":
        return _attributes_from(instance, MENTOR_FIELDS)
    return None


def brevo_list_id_for(instance) -> int | None:
    if instance.__class__.__name__ == "Mentor":
        return settings.BREVO_MENTOR_LIST_ID
    return None
