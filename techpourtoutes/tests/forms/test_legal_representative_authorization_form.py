from techpourtoutes.forms import LegalRepresentativeAuthorizationForm

VALID_DATA = {
    "legal_representative_name": "Marie Petit",
    "relationship": "mother",
    "authorization_confirmed": "on",
    "terms_accepted": "on",
}


def test_a_signature_needs_a_name_a_relationship_and_both_confirmations():
    form = LegalRepresentativeAuthorizationForm(data={})

    assert not form.is_valid()
    assert set(form.errors) == {
        "legal_representative_name",
        "relationship",
        "authorization_confirmed",
        "terms_accepted",
    }


def test_the_newsletter_is_optional():
    form = LegalRepresentativeAuthorizationForm(data=VALID_DATA)

    assert form.is_valid()
    assert form.cleaned_data["newsletter_consent"] is False


def test_the_relationship_offers_the_four_legal_representatives():
    choices = LegalRepresentativeAuthorizationForm().fields["relationship"].choices

    assert [label for _, label in choices] == [
        "Sélectionner une option",
        "Mère",
        "Père",
        "Tuteur ou tutrice légale",
        "Autre représentant légal",
    ]
