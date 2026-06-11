from typing import Any, ClassVar

from django import forms
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from ...models import Pro, User


class BaseEngagementForm(forms.Form):
    """Shared form for the engagement flows that create or update a `Pro`.

    Every engagement (workshop, training ambassador, generic) collects the same
    identity fields plus its own professional fields, then writes them onto a
    `Pro`. Subclasses tailor the behaviour through three class attributes:

    - `pro_fields`: form fields whose cleaned values are copied onto the `Pro`.
    - `pro_constants`: `Pro` attributes forced to a fixed value regardless of
      user input (e.g. a professional situation implied by the engagement).
    - `prefill_fields`: extra fields, on top of the identity fields and email,
      to prefill when editing an existing `Pro`.

    Passing an existing `pro` switches the form into edit mode: its fields are
    prefilled, the email becomes read-only, and the terms checkbox is no longer
    required (the user already accepted them at sign-up).
    """

    # Identity fields written onto every Pro, whatever the engagement.
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
    manifeste_accepted = forms.BooleanField(
        label=_("J'adhère au manifeste TechPourToutes"),
        required=True,
        error_messages={
            "required": _("Vous devez adhérer au manifeste pour continuer."),
        },
    )

    def __init__(self, *args, pro=None, **kwargs):
        if pro is not None:
            kwargs.setdefault("initial", self._prefilled_values_from(pro))
        super().__init__(*args, **kwargs)
        self.pro = pro
        self.fields["terms_accepted"].label = format_html(
            "J'accepte la création de mon compte, les "
            "<a href='{}' class='underline' target='_blank'>conditions d'utilisation</a>"
            " et la "
            "<a href='{}' class='underline' target='_blank'>"
            "politique de gestion des données personnelles"
            "</a>",
            reverse_lazy("conditions_generales"),
            reverse_lazy("donnees_personnelles"),
        )
        self.fields["manifeste_accepted"].label = format_html(
            "J'adhère au "
            "<a href='{}' class='underline' target='_blank'>manifeste TechPourToutes</a>",
            reverse_lazy("notre_manifeste"),
        )
        if pro is not None:
            self._lock_fields_for_existing_account()

    def clean_email(self):
        email = self.cleaned_data["email"]
        if self._email_taken_by_another_account(email):
            raise forms.ValidationError(_("Un compte avec cet email existe déjà."))
        return email

    def save(self, commit=True):
        pro = self._get_or_build_pro()
        self._copy_form_fields_onto(pro)
        self._apply_constants_onto(pro)
        if commit:
            pro.save()
        return pro

    def after_save(self, pro):
        """Hook for subclasses to persist objects related to the saved Pro."""

    # ------------------- private methods -------------------

    def _prefilled_values_from(self, pro):
        fields = (*self.BASE_FIELDS, "email", *self.prefill_fields)
        values = {field: getattr(pro, field) for field in fields}
        if "phone" in values:
            values["phone"] = pro.phone.as_national if pro.phone else ""
        return values

    def _lock_fields_for_existing_account(self):
        # The email identifies the account; terms and manifeste were accepted at sign-up.
        self.fields["email"].disabled = True
        self.fields["terms_accepted"].required = False
        self.fields["manifeste_accepted"].required = False

    def _email_taken_by_another_account(self, email):
        if self.pro and email == self.pro.email:
            return False
        return User.objects.filter(email=email).exists()

    def _get_or_build_pro(self):
        email = self.cleaned_data["email"]
        return self.pro or Pro(username=email, email=email)

    def _copy_form_fields_onto(self, pro):
        for field in (*self.BASE_FIELDS, *self.pro_fields):
            setattr(pro, field, self.cleaned_data[field])

    def _apply_constants_onto(self, pro):
        for attr, value in self.pro_constants.items():
            setattr(pro, attr, value)
