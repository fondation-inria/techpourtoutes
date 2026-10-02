from django import forms


class BeneficiaryTrainingAmbassadorRequestForm(forms.Form):
    topic = forms.CharField(
        max_length=1000,
        label="",
        widget=forms.Textarea(),
    )
