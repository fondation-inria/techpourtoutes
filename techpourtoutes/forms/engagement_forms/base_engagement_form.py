from typing import Any, ClassVar

from django import forms
from django.utils.translation import gettext_lazy as _

from ...models import Pro, User


class BaseEngagementForm(forms.Form):
    BASE_FIELDS = ("civility", "first_name", "last_name")

    pro_fields: ClassVar[tuple[str, ...]] = ()
    pro_constants: ClassVar[dict[str, Any]] = {}
    prefill_fields: ClassVar[tuple[str, ...]] = ()

    civility = forms.ChoiceField(label=_("Votre civilité*"), choices=Pro.Civility.choices)
    first_name = forms.CharField(label=_("Votre prénom*"))
    last_name = forms.CharField(label=_("Votre nom*"))
    email = forms.EmailField(
        label=_("Votre email*"),
        error_messages={"invalid": _("Saisissez une adresse mail valide.")},
    )
    terms_accepted = forms.BooleanField(
        label=_(
            "J'accepte la création de mon compte, les conditions d'utilisation et la "
            "politique de gestion des données personnelles"
        ),
        required=True,
        error_messages={
            "required": _("Vous devez accepter les conditions d'utilisation pour continuer."),
        },
    )

    def __init__(self, *args, pro=None, **kwargs):
        if pro is not None:
            kwargs.setdefault("initial", self._initial_from_pro(pro))
        super().__init__(*args, **kwargs)
        self.pro = pro
        if pro is not None:
            self.fields["email"].disabled = True
            self.fields["terms_accepted"].required = False

    def _initial_from_pro(self, pro):
        fields = (*self.BASE_FIELDS, "email", *self.prefill_fields)
        initial = {field: getattr(pro, field) for field in fields}
        if "phone" in initial:
            initial["phone"] = pro.phone.as_national if pro.phone else ""
        return initial

    def clean_email(self):
        email = self.cleaned_data["email"]
        if (
            not (self.pro and email == self.pro.email)
            and User.objects.filter(email=email).exists()
        ):
            raise forms.ValidationError(_("Un compte avec cet email existe déjà."))
        return email

    def save(self, commit=True):
        data = self.cleaned_data
        pro = self.pro or Pro(username=data["email"], email=data["email"])
        for field in (*self.BASE_FIELDS, *self.pro_fields):
            setattr(pro, field, data[field])
        for attr, value in self.pro_constants.items():
            setattr(pro, attr, value)
        if commit:
            pro.save()
        return pro
