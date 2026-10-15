from django import forms


class BeneficiaryMakeuseProjectRequestForm(forms.Form):
    project_name = forms.CharField(
        max_length=1000,
        label="Nom du projet*",
    )
    project_link = forms.URLField(
        max_length=1000,
        label="Lien vers le projet ou vers une présentation de celui-ci*",
    )
    project_description = forms.CharField(
        max_length=1000,
        label="Description succincte du projet*",
        widget=forms.Textarea(),
    )
