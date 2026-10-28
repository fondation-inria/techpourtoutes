from django import forms
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from ...models import User


class ProIdentityForm(forms.Form):
    civility = forms.ChoiceField(
        label=_("Civilité*"),
        choices=User.Civility.choices,
    )
    first_name = forms.CharField(label=_("Votre prénom*"))
    last_name = forms.CharField(label=_("Votre nom*"))
    manifeste_accepted = forms.BooleanField(
        required=True,
        error_messages={"required": _("Vous devez adhérer au manifeste pour continuer.")},
    )
    newsletter_consent = forms.BooleanField(
        label=_("Oui, je veux recevoir ponctuellement des nouvelles de TechPourToutes."),
        required=False,
    )
    terms_accepted = forms.BooleanField(
        required=True,
        error_messages={
            "required": _("Vous devez accepter les conditions d'utilisation pour continuer."),
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["manifeste_accepted"].label = format_html(
            "J'adhère au "
            "<a href='{}' class='inline-link' target='_blank'>manifeste TechPourToutes</a>*",
            reverse_lazy("notre_manifeste"),
        )
        self.fields["terms_accepted"].label = format_html(
            "J'accepte les "
            "<a href='{}' class='inline-link' target='_blank'>conditions d'utilisation</a>"
            " et la "
            "<a href='{}' class='inline-link' target='_blank'>"
            "politique de gestion des données personnelles"
            "</a> de TechPourToutes.*",
            reverse_lazy("conditions_generales"),
            reverse_lazy("donnees_personnelles"),
        )
