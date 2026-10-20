import re

from django.core.files.storage import storages
from django.forms import CharField, HiddenInput, ValidationError
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


class UploadedImageKeyField(CharField):
    """The key of an image the browser uploaded straight to the public bucket. It comes back
    from the browser: it has to name a file `CreatePresignedUpload` signed under `prefix`, not
    any file of the bucket."""

    widget = HiddenInput

    def __init__(self, *, prefix, **kwargs):
        self.key_pattern = re.compile(rf"{re.escape(prefix)}/[0-9a-f]{{32}}\.\w+")
        super().__init__(required=False, **kwargs)

    def validate(self, value):
        super().validate(value)
        if value and not (self.key_pattern.fullmatch(value) and storages["public"].exists(value)):
            raise ValidationError(_("Ce visuel est introuvable, importez-le à nouveau."))
