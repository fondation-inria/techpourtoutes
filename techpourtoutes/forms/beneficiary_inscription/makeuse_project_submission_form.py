from django import forms


class BeneficiaryMakeuseProjectSubmissionForm(forms.Form):
    project_name = forms.CharField(
        max_length=1000,
        label="Nom du projet*",
    )
    project_link = forms.URLField(
        max_length=1000,
        label="Lien vers le projet ou vers une présentation de celui-ci*",
        error_messages={
            "invalid": "Saisis un lien valide. Exemple d'url valide : www.techpourtoutes.io",
        },
    )
    project_description = forms.CharField(
        max_length=3000,
        label="Description succincte du projet*",
        widget=forms.Textarea(),
    )
