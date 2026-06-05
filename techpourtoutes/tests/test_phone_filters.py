from phonenumber_field.phonenumber import PhoneNumber

from techpourtoutes.templatetags.phone_filters import phone_national


def test_phone_national_french_number():
    phone = PhoneNumber.from_string("+33612345678")
    assert phone_national(phone) == "06 12 34 56 78"


def test_phone_national_empty_values():
    assert phone_national("") == ""
    assert phone_national(None) == ""
