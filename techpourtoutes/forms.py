from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from .models import Mentor, User


class MentorForm(forms.Form):
    first_name = forms.CharField(label=_("Votre prénom*"))
    last_name = forms.CharField(label=_("Votre nom*"))
    email = forms.EmailField(label=_("Votre email*"))
    phone = PhoneNumberField(region="FR", label=_("Votre n° de téléphone*"))
    professional_situation = forms.CharField(label=_("Votre situation professionnelle*"))
    structure_name = forms.CharField(label=_("Nom de votre structure"), required=False)
    job_title = forms.CharField(label=_("Votre métier*"))
    postal_code = forms.CharField(
        label=_("Votre code postal*"),
        validators=[RegexValidator(r"^\d{5}$", _("Entrez un code postal valide à 5 chiffres."))],
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Un compte avec cet email existe déjà."))
        return email

    def save(self):
        data = self.cleaned_data
        mentor = Mentor(
            username=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            phone=data["phone"],
            professional_situation=data["professional_situation"],
            structure_name=data["structure_name"],
            job_title=data["job_title"],
            postal_code=data["postal_code"],
        )
        mentor.save()
        return mentor
