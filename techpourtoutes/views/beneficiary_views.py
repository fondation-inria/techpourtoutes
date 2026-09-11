from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef, Value
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from ..forms import (
    BeneficiaryHigherEducationTrainingExperienceForm,
    BeneficiaryHighSchoolTrainingExperienceForm,
    BeneficiaryLastDiplomaTrainingExperienceForm,
    StudyStatus,
    UpcomingFeatureNotificationForm,
)
from ..models import Event, SavedEvent
from ..tasks import create_upcoming_feature_notification_task
from ..utils.dates import compute_age

EVENTS_PER_PAGE = 15

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


def index_events(request):
    return render(
        request,
        "beneficiary/index_events.html",
        _events_context(request, page=request.GET.get("page")),
    )


def show_event(request, pk):
    beneficiary = getattr(request.user, "beneficiary", None)
    event = get_object_or_404(Event.objects.approved(), pk=pk)
    return render(
        request,
        "beneficiary/show_event.html",
        {
            "event": event,
            "saved": _is_saved(beneficiary, event),
            "bookmark_action": _bookmark_action(request.user, beneficiary),
        },
    )


@require_POST
@login_required
def update_saved_event(request, pk):
    beneficiary = _beneficiary_or_404(request)
    event = get_object_or_404(Event.objects.approved(), pk=pk)
    label = request.POST.get("label") == "true"
    saved = SavedEvent.objects.toggle(event=event, beneficiary=beneficiary)
    messages.success(request, "Événement enregistré" if saved else "Événement retiré")
    return render(
        request,
        "beneficiary/partials/update_saved_event.html",
        {
            "event": event,
            "saved": saved,
            "bookmark_action": "toggle",
            "label": label,
        },
    )


def create_saved_event_modal(request):
    return render(request, "beneficiary/partials/create_saved_event_modal.html", {})


def show_participation_modal(request, pk):
    beneficiary = getattr(request.user, "beneficiary", None)
    event = get_object_or_404(Event.objects.approved(), pk=pk)
    return render(
        request,
        "beneficiary/partials/show_participation_modal.html",
        {
            "event": event,
            "is_candidacy": event.access_type == Event.AccessType.CANDIDACY,
            "saved": _is_saved(beneficiary, event),
            "bookmark_action": _bookmark_action(request.user, beneficiary),
        },
    )


def _render_upcoming_feature_notification_form(request, form):
    return render(request, "beneficiary/new_upcoming_feature_notification.html", {"form": form})


# ------------------- events -------------------


def _events_context(request, page):
    beneficiary = getattr(request.user, "beneficiary", None)
    return {
        "events": _events_page(beneficiary, page),
        "bookmark_action": _bookmark_action(request.user, beneficiary),
    }


def _events_page(beneficiary, page):
    """Only one query: each event carries whether the visitor already bookmarked it."""
    upcoming = Event.objects.approved().upcoming()
    if beneficiary is None:
        upcoming = upcoming.annotate(saved=Value(False))
    else:
        upcoming = upcoming.annotate(
            saved=Exists(SavedEvent.objects.filter(event=OuterRef("pk"), beneficiary=beneficiary))
        )
    return Paginator(upcoming, EVENTS_PER_PAGE).get_page(page)


def _bookmark_action(user, beneficiary):
    """Only a beneficiary can save an event; a signed-in pro is not invited to try."""
    if beneficiary is not None:
        return "toggle"
    return "" if user.is_authenticated else "signup"


def _is_saved(beneficiary, event):
    return (
        beneficiary is not None
        and SavedEvent.objects.filter(event=event, beneficiary=beneficiary).exists()
    )


def _beneficiary_or_404(request):
    beneficiary = getattr(request.user, "beneficiary", None)
    if beneficiary is None:
        raise Http404
    return beneficiary


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
