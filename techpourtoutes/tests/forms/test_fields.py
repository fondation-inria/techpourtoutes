from techpourtoutes.forms.fields import EmailField


def test_email_field_lowercases_the_address():
    assert EmailField().clean("Alice@Example.COM") == "alice@example.com"


def test_email_field_leaves_an_omitted_optional_value_alone():
    assert EmailField(required=False).clean("") == ""
