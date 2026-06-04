from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from ..models import Pro, User


class ProForm(forms.Form):
    civility = forms.ChoiceField(label=_("Votre civilité*"), choices=Pro.Civility.choices)
    first_name = forms.CharField(label=_("Votre prénom*"))
    last_name = forms.CharField(label=_("Votre nom*"))
    email = forms.EmailField(
        label=_("Votre email*"),
        error_messages={"invalid": _("Saisissez une adresse mail valide.")},
    )
    phone = PhoneNumberField(region="FR", label=_("Votre n° de téléphone*"))
    postal_code = forms.CharField(
        label=_("Votre code postal*"),
        validators=[RegexValidator(r"^\d{5}$", _("Entrez un code postal valide à 5 chiffres."))],
    )
    professional_situation = forms.ChoiceField(
        label=_("Votre situation professionnelle*"),
        choices=[("", _("Sélectionner une option"))]
        + [c for c in Pro.ProfessionalSituation.choices if c[0] != "student"],
    )
    structure_name = forms.CharField(label=_("Nom de votre structure*"), required=False)
    job_title = forms.CharField(label=_("Votre métier*"))
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
            kwargs.setdefault(
                "initial",
                {
                    "civility": pro.civility,
                    "first_name": pro.first_name,
                    "last_name": pro.last_name,
                    "email": pro.email,
                    "phone": str(pro.phone),
                    "postal_code": pro.postal_code,
                    "professional_situation": pro.professional_situation,
                    "structure_name": pro.structure_name,
                    "job_title": pro.job_title,
                },
            )
        super().__init__(*args, **kwargs)
        self.pro = pro
        if pro is not None:
            self.fields["email"].disabled = True
            self.fields["terms_accepted"].required = False

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("professional_situation") == "working":
            structure_fields = ("structure_name",)
            for field in structure_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, _("Ce champ est obligatoire."))
        return cleaned_data

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
        if self.pro is not None:
            pro = self.pro
            pro.civility = data["civility"]
            pro.first_name = data["first_name"]
            pro.last_name = data["last_name"]
            pro.phone = data["phone"]
            pro.postal_code = data["postal_code"]
            pro.professional_situation = data["professional_situation"]
            pro.structure_name = data["structure_name"]
            pro.job_title = data["job_title"]
        else:
            pro = Pro(
                username=data["email"],
                civility=data["civility"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                phone=data["phone"],
                postal_code=data["postal_code"],
                professional_situation=data["professional_situation"],
                structure_name=data["structure_name"],
                job_title=data["job_title"],
            )
        if commit:
            pro.save()
        return pro
