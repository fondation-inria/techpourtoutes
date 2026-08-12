import phonenumbers

# Onisep lists mainland France and the overseas territories in a single column, and
# libphonenumber only accepts an overseas number when parsed under its own region.
REGIONS = ("FR", "RE", "GP", "GF", "MQ", "YT", "PM", "NC", "PF", "WF", "BL", "MF")


def parse_school_phone(value: str | None) -> str:
    """Normalize an Onisep phone number to E.164, dropping what cannot be dialled.

    Short service numbers ("39 36") and typos are returned as an empty string rather than
    stored as-is, so the column only ever holds numbers `PhoneNumberField` accepts.
    """
    for region in REGIONS:
        try:
            number = phonenumbers.parse(value or "", region)
        except phonenumbers.NumberParseException:
            return ""
        if phonenumbers.is_valid_number(number):
            return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
    return ""
