from techpourtoutes.forms import ProIdentityForm


def _identity(**overrides):
    return {
        "civility": "Madame",
        "first_name": "Hedy",
        "last_name": "Lamarr",
        "manifeste_accepted": "on",
        "terms_accepted": "on",
        **overrides,
    }


def test_identity_form_accepts_a_complete_identity():
    assert ProIdentityForm(data=_identity()).is_valid()


def test_identity_form_requires_a_civility():
    form = ProIdentityForm(data=_identity(civility=""))
    assert not form.is_valid()
    assert "civility" in form.errors


def test_identity_form_requires_the_manifeste_and_the_terms():
    form = ProIdentityForm(data=_identity(manifeste_accepted="", terms_accepted=""))
    assert not form.is_valid()
    assert "manifeste_accepted" in form.errors
    assert "terms_accepted" in form.errors


def test_identity_form_leaves_the_newsletter_optional():
    form = ProIdentityForm(data=_identity())
    assert form.is_valid()
    assert form.cleaned_data["newsletter_consent"] is False
