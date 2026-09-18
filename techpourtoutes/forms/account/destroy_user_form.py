from django import forms


class DestroyUserForm(forms.Form):
    confirm_delete = forms.BooleanField(
        required=True,
        label="Je confirme vouloir supprimer mon compte TechPourToutes",
        error_messages={"required": "Vous devez confirmer la suppression de votre compte."},
    )
