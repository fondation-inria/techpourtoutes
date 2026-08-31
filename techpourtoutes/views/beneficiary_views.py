from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from ..forms import (
    BeneficiaryHigherEducationTrainingExperienceForm,
    BeneficiaryHighSchoolTrainingExperienceForm,
    BeneficiaryLastDiplomaTrainingExperienceForm,
    EmailNotificationForm,
    StudyStatus,
)
from ..tasks import upsert_email_notification_task
from ..utils.dates import compute_age

# ------------------- pages -------------------


def beneficiary_home(request):
    return render(request, "beneficiary/beneficiary_home.html", {})


def bientot_disponible(request):
    if request.method == "POST":
        form = EmailNotificationForm(data=request.POST)
        if form.is_valid():
            if settings.BREVO_SYNC_ENABLED:
                upsert_email_notification_task.delay(email=form.cleaned_data["email"])
            messages.success(
                request,
                "Merci, nous te préviendrons dès que cette fonctionnalité sera disponible.",
            )
            return redirect("bientot_disponible")
        messages.error(
            request,
            "Des erreurs empêchent la validation du formulaire, "
            "merci de les corriger et de réessayer à nouveau.",
        )
    else:
        form = EmailNotificationForm()
    return render(request, "beneficiary/bientot_disponible.html", {"form": form})


def find_mentor_landing(request):
    beneficiary = getattr(request.user, "beneficiary", None)
    cta_href = reverse("add_mentoring")
    cta_label = "S'inscrire au mentorat"
    cta_disabled = False
    if not request.user.is_authenticated:
        cta_href = f"{reverse('inscription_funnel')}?wants_mentor=1"
    if beneficiary is not None:
        if beneficiary.jobirl_user_id:
            cta_href = reverse("login_to_jobirl")
            cta_label = "Rejoindre mon espace mentorat"
        elif beneficiary.legal_representative_email:
            cta_href = ""
            cta_label = "Rejoindre mon espace mentorat"
            cta_disabled = True
    return render(
        request,
        "beneficiary/find_mentor_landing.html",
        {"cta_href": cta_href, "cta_label": cta_label, "cta_disabled": cta_disabled},
    )


# ------------------- steps shared by both funnels -------------------

# The inscription funnel (views/beneficiary/inscription_views.py) and the mentoring one
# (views/beneficiary/mentoring_views.py) ask the same three questions and render the same field
# partials (partials/inscription/*_fields.html); what feeds them lives here. Only where an answer
# comes from — the browser's sessionStorage or the account — stays funnel-specific.

TRAINING_EXPERIENCE_FORMS = {
    StudyStatus.HIGH_SCHOOL: BeneficiaryHighSchoolTrainingExperienceForm,
    StudyStatus.HIGHER_EDUCATION: BeneficiaryHigherEducationTrainingExperienceForm,
    StudyStatus.FINISHED: BeneficiaryLastDiplomaTrainingExperienceForm,
    StudyStatus.RESUMING: BeneficiaryLastDiplomaTrainingExperienceForm,
}


def training_experience_context(study_status, form=None, initial=None):
    return {
        "study_status": study_status,
        "form": form or TRAINING_EXPERIENCE_FORMS[study_status](initial=initial),
    }


def is_minor(birth_date):
    return birth_date is not None and compute_age(birth_date) < 18


def require_legal_representative(form, minor):
    if not (form.is_valid() and minor):
        return
    for field in ("legal_representative_name", "legal_representative_email"):
        if not form.cleaned_data[field]:
            form.add_error(field, "Ce champ est obligatoire.")


def relay_errors(request, result):
    for error in result.errors:
        messages.error(request, error)
