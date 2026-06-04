from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Pro, User, WorkshopRequest

FONCTION_CHOICES = [
    ("", _("Sélectionner une option")),
    ("Enseignante", _("Enseignante")),
    ("Documentaliste", _("Documentaliste")),
    ("CPE", _("CPE")),
    ("Responsable établissement", _("Responsable établissement")),
    ("Référente mission EDD", _("Référente mission EDD")),
    ("DRANE / DAN / IAN", _("DRANE / DAN / IAN")),
    ("Autre mission au sein d'un établissement", _("Autre mission au sein d'un établissement")),
    ("parent d'élèves", _("Parent d'élève")),
    ("je ne travaille pas dans un établissement", _("Je ne travaille pas dans un établissement")),
]


class WorkshopForm(forms.Form):
    civility = forms.ChoiceField(label=_("Votre civilité*"), choices=Pro.Civility.choices)
    first_name = forms.CharField(label=_("Votre prénom*"))
    last_name = forms.CharField(label=_("Votre nom*"))
    email = forms.EmailField(
        label=_("Votre email*"),
        error_messages={"invalid": _("Saisissez une adresse mail valide.")},
    )
    structure_id = forms.CharField(widget=forms.HiddenInput)
    structure_name = forms.CharField(label=_("Établissement*"))
    postal_code = forms.CharField(widget=forms.HiddenInput)
    job_title = forms.ChoiceField(label=_("Fonction*"), choices=FONCTION_CHOICES)
    remark = forms.CharField(label=_("Remarque"), required=False, widget=forms.Textarea)
    ateliers = forms.MultipleChoiceField(
        label=_("Atelier demandé*"),
        choices=WorkshopRequest.Type.choices,
        widget=forms.CheckboxSelectMultiple,
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
            kwargs.setdefault(
                "initial",
                {
                    "civility": pro.civility,
                    "first_name": pro.first_name,
                    "last_name": pro.last_name,
                    "email": pro.email,
                },
            )
        super().__init__(*args, **kwargs)
        self.pro = pro
        if pro is not None:
            self.fields["email"].disabled = True
            self.fields["terms_accepted"].required = False

    def clean_email(self):
        email = self.cleaned_data["email"]
        if self.pro and email == self.pro.email:
            return email
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _("Un compte avec cet email existe déjà."), code="email_exists"
            )
        return email

    def save(self, commit=True):
        data = self.cleaned_data
        if self.pro is not None:
            pro = self.pro
            pro.civility = data["civility"]
            pro.first_name = data["first_name"]
            pro.last_name = data["last_name"]
            pro.professional_situation = Pro.ProfessionalSituation.WORKING
            pro.structure_name = data["structure_name"]
            pro.structure_id = data["structure_id"]
            pro.job_title = data["job_title"]
            pro.postal_code = data["postal_code"]
        else:
            pro = Pro(
                username=data["email"],
                civility=data["civility"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                professional_situation=Pro.ProfessionalSituation.WORKING,
                structure_name=data["structure_name"],
                structure_id=data["structure_id"],
                job_title=data["job_title"],
                postal_code=data["postal_code"],
            )
        if commit:
            pro.save()
        return pro
