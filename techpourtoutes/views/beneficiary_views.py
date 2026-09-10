from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from ..forms import (
    BeneficiaryHigherEducationTrainingExperienceForm,
    BeneficiaryHighSchoolTrainingExperienceForm,
    BeneficiaryLastDiplomaTrainingExperienceForm,
    StudyStatus,
    UpcomingFeatureNotificationForm,
)
from ..tasks import create_upcoming_feature_notification_task
from ..utils.dates import compute_age

# ------------------- pages -------------------


def beneficiary_home(request):
    return render(request, "beneficiary/beneficiary_home.html", {})


def new_upcoming_feature_notification(request):
    return _render_upcoming_feature_notification_form(request, UpcomingFeatureNotificationForm())


@require_POST
def create_upcoming_feature_notification(request):
    form = UpcomingFeatureNotificationForm(data=request.POST)
    if not form.is_valid():
        messages.error(
            request,
            "Des erreurs empêchent la validation du formulaire, "
            "merci de les corriger et de réessayer à nouveau.",
        )
        return _render_upcoming_feature_notification_form(request, form)

    if settings.BREVO_SYNC_ENABLED:
        create_upcoming_feature_notification_task.delay(email=form.cleaned_data["email"])
    messages.success(
        request,
        "Merci, nous te préviendrons dès que cette fonctionnalité sera disponible.",
    )
    return redirect("new_upcoming_feature_notification")


def new_mentoree(request):
    beneficiary = getattr(request.user, "beneficiary", None)
    cta_href = reverse("mentoring_funnel")
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
        "beneficiary/new_mentoree.html",
        {"cta_href": cta_href, "cta_label": cta_label, "cta_disabled": cta_disabled},
    )


def _render_upcoming_feature_notification_form(request, form):
    return render(request, "beneficiary/new_upcoming_feature_notification.html", {"form": form})


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
