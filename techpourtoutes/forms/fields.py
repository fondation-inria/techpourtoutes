from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField as BasePhoneNumberField

INVALID_PHONE_NUMBER_MESSAGE = _(
    "Le numéro de téléphone saisi est invalide. Il doit correspondre par exemple à "
    "01\xa023\xa045\xa067\xa089, ou avoir un numéro avec un indicatif international."
)


class PhoneNumberField(BasePhoneNumberField):
    default_error_messages = {"invalid": INVALID_PHONE_NUMBER_MESSAGE}
