from django import forms
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class BeneficiaryIdentityForm(forms.Form):
    first_name = forms.CharField(label=_("Ton prénom*"))
    last_name = forms.CharField(label=_("Ton nom*"))
    birth_date = forms.DateField(
        label=_("Ta date de naissance*"), input_formats=["%Y-%m-%d", "%d/%m/%Y"]
    )
    age_eligibility_accepted = forms.BooleanField(
        label=_(
            "J'ai compris que ce programme s'adresse exclusivement aux filles entre 15 et 25 ans."
        ),
        required=True,
        error_messages={
            "required": _("Tu dois confirmer être éligible au programme pour continuer."),
        },
    )
    newsletter_consent = forms.BooleanField(
        label=_(
            "Oui, je veux recevoir des conseils et des actualités de la part de "
            "l'équipe TechPourToutes."
        ),
        required=False,
    )
    terms_accepted = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["age_eligibility_accepted"].label = format_html(
            "{}*", self.fields["age_eligibility_accepted"].label
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
