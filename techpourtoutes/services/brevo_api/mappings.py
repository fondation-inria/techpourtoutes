from datetime import date, datetime

from django.apps import apps
from django.conf import settings
from phonenumber_field.phonenumber import PhoneNumber

BREVO_MULTIPLE_CHOICE_FIELDS = {"civility", "professional_situation", "engagements"}

BREVO_PRO_CONSTANT_ATTRIBUTES = {
    "TYPES_DE_CONTACT": ["Coalition TPT"],
}

FIELD_TO_BREVO_ATTR = {
    "email": "EMAIL",
    "first_name": "PRENOM",
    "last_name": "NOM",
    "phone": "SMS",
    "civility": "CIVILITE",
    "job_title": "JOB_TITLE",
    "professional_situation": "SITUATION_PRO",
    "structure_name": "NOM_DE_LA_STRUCTURE",
    "postal_code": "CODE_POSTAL",
    "engagements": "ENGAGEMENTS",
}

USER_FIELDS = ["email", "first_name", "last_name"]

PRO_FIELDS = USER_FIELDS + [
    "phone",
    "civility",
    "job_title",
    "professional_situation",
    "structure_name",
    "postal_code",
    "engagements",
]


def brevo_attributes_for(instance) -> dict | None:
    if _is_pro(instance):
        attrs = _attributes_from(instance, PRO_FIELDS)
        if instance.phone:
            attrs["TELEPHONE_RAW_NUMBER"] = instance.phone.as_e164.replace("+", "00")
        return {**attrs, **BREVO_PRO_CONSTANT_ATTRIBUTES}
    return None


def brevo_attributes_for_manifeste_signatory(
    *, first_name, last_name, email, structure_name
) -> dict:
    return {
        FIELD_TO_BREVO_ATTR["email"]: email,
        FIELD_TO_BREVO_ATTR["first_name"]: first_name,
        FIELD_TO_BREVO_ATTR["last_name"]: last_name,
        FIELD_TO_BREVO_ATTR["structure_name"]: structure_name,
        **BREVO_PRO_CONSTANT_ATTRIBUTES,
    }


def brevo_list_id_for(instance) -> int | None:
    if _is_pro(instance):
        return settings.BREVO_PRO_LIST_ID
    return None


# ------------------- private -------------------


def _is_pro(instance) -> bool:
    return isinstance(instance, apps.get_model("techpourtoutes", "Pro"))


def _attributes_from(instance, fields: list[str]) -> dict:
    result = {}
    for field in fields:
        value = _serialize(getattr(instance, field))
        if field in BREVO_MULTIPLE_CHOICE_FIELDS:
            field_meta = instance._meta.get_field(field)
            choices = dict(getattr(field_meta, "base_field", field_meta).choices)
            value = [str(choices[v]) for v in (value if isinstance(value, list) else [value])]
        attribute = FIELD_TO_BREVO_ATTR[field]
        if isinstance(attribute, list):
            for attr_name in attribute:
                result[attr_name] = value
        else:
            result[attribute] = value
    return result


def _serialize(value):
    if value is None:
        return None
    if isinstance(value, PhoneNumber):
        return value.as_e164
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value
