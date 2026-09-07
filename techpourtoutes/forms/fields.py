from django.forms import EmailField as BaseEmailField
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField as BasePhoneNumberField

INVALID_PHONE_NUMBER_MESSAGE = _(
    "Le numéro de téléphone saisi est invalide. Il doit correspondre par exemple à "
    "01\xa023\xa045\xa067\xa089, ou avoir un numéro avec un indicatif international."
)


class PhoneNumberField(BasePhoneNumberField):
    default_error_messages = {"invalid": INVALID_PHONE_NUMBER_MESSAGE}


class EmailField(BaseEmailField):
    """Lowercase the address so lookups match how `User.save` stores it."""

    def to_python(self, value):
        value = super().to_python(value)
        return value.lower() if value else value
