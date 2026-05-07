from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from .models import Mentor, User


class MentorForm(forms.Form):
    civility = forms.ChoiceField(label=_("Votre civilité*"), choices=Mentor.Civility.choices)
    first_name = forms.CharField(label=_("Votre prénom*"))
    last_name = forms.CharField(label=_("Votre nom*"))
    birth_date = forms.DateField(label=_("Votre date de naissance*"))
    email = forms.EmailField(label=_("Votre email*"))
    phone = PhoneNumberField(region="FR", label=_("Votre n° de téléphone*"))
    address = forms.CharField(label=_("Votre adresse*"))
    postal_code = forms.CharField(
        label=_("Votre code postal*"),
        validators=[RegexValidator(r"^\d{5}$", _("Entrez un code postal valide à 5 chiffres."))],
    )
    city = forms.CharField(label=_("Votre ville*"))
    professional_situation = forms.ChoiceField(
        label=_("Votre situation professionnelle*"),
        choices=[("", _("Sélectionner une option")), *Mentor.ProfessionalSituation.choices],
    )
    structure_name = forms.CharField(label=_("Nom de votre structure"), required=False)
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

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Un compte avec cet email existe déjà."))
        return email

    def save(self, commit=True):
        data = self.cleaned_data
        mentor = Mentor(
            username=data["email"],
            civility=data["civility"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            birth_date=data["birth_date"],
            email=data["email"],
            phone=data["phone"],
            address=data["address"],
            postal_code=data["postal_code"],
            city=data["city"],
            professional_situation=data["professional_situation"],
            structure_name=data["structure_name"],
            job_title=data["job_title"],
        )
        if commit:
            mentor.save()
        return mentor
