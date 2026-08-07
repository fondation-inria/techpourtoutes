from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class EmailChangeForm(forms.Form):
    email = forms.EmailField(label=_("Nouvelle adresse mail"))

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if email.casefold() == self.user.email.casefold():
            raise forms.ValidationError(_("Cette adresse est déjà la vôtre."))
        clashes = (
            get_user_model()
            .all_objects.filter(Q(email__iexact=email) | Q(username__iexact=email))
            .exclude(pk=self.user.pk)
        )
        if clashes.exists():
            raise forms.ValidationError(_("Cette adresse mail est déjà utilisée."))
        return email
