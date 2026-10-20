from django import forms
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from ..models import LegalRepresentativeAuthorization


class LegalRepresentativeAuthorizationForm(forms.Form):
    legal_representative_name = forms.CharField(max_length=150, label=_("Nom*"))
    relationship = forms.ChoiceField(
        choices=[
            ("", _("Sélectionner une option")),
            *LegalRepresentativeAuthorization.Relationship.choices,
        ],
        label=_("Vous êtes*"),
    )
    authorization_confirmed = forms.BooleanField(
        label=_("Je confirme donner mon autorisation en tant que personne responsable légale.*"),
        error_messages={"required": _("Vous devez confirmer votre autorisation.")},
    )
    terms_accepted = forms.BooleanField(
        error_messages={
            "required": _("Vous devez accepter la politique de gestion des données personnelles.")
        },
    )
    newsletter_consent = forms.BooleanField(
        label=_(
            "Je souhaite recevoir les actus de TechPourToutes et découvrir ses prochaines "
            "initiatives."
        ),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["terms_accepted"].label = format_html(
            "J'accepte la "
            "<a href='{}' class='inline-link' target='_blank'>"
            "politique de gestion des données personnelles"
            "</a> de TechPourToutes.*",
            reverse_lazy("donnees_personnelles"),
        )
