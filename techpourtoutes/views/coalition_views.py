from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..forms import (
    EngagementForm,
    ManifesteSignatureForm,
    TrainingAmbassadorForm,
    WorkshopForm,
)
from ..mailers import ConsortiumMailer, ProMailer
from ..models import Pro, WorkshopRequest
from ..services.pro.create_mentor import CreateMentor
from ..tasks import notify_workshop_request_task, upsert_manifeste_signatory_task
from ..utils.missing_record import report_missing_record

MENTOR_TEMPLATE = "coalition/new_mentor.html"
WORK_AMBASSADOR_TEMPLATE = "coalition/new_work_ambassador.html"
TRAINING_AMBASSADOR_TEMPLATE = "coalition/new_training_ambassador.html"
SPONSOR_TEMPLATE = "coalition/new_sponsor.html"
WORKSHOP_TEMPLATE = "coalition/new_workshop_request.html"
MANIFESTE_TEMPLATE = "coalition/new_manifeste_signature.html"


def coalition_home(request):
    return render(request, "coalition/coalition_home.html", {})


def new_mentor(request):
    return _render_engagement_form(request, EngagementForm, MENTOR_TEMPLATE)


@require_POST
def create_mentor(request):
    pro = _current_pro(request)
    form = EngagementForm(data=request.POST, pro=pro)
    if not form.is_valid():
        return _reject_engagement_form(request, form, pro, MENTOR_TEMPLATE)

    result = CreateMentor(pro=form.save(commit=False))
    if result.failure:
        for error in result.errors:
            messages.error(request, error)
        return render(request, MENTOR_TEMPLATE, {"form": form, "pro": pro})
    return redirect("coalition_welcome")


def new_work_ambassador(request):
    return _render_engagement_form(request, EngagementForm, WORK_AMBASSADOR_TEMPLATE)


@require_POST
def create_work_ambassador(request):
    return _create_engagement(
        request,
        form_class=EngagementForm,
        engagement=Pro.Engagement.WORK_AMBASSADOR,
        template=WORK_AMBASSADOR_TEMPLATE,
    )


def new_training_ambassador(request):
    return _render_engagement_form(request, TrainingAmbassadorForm, TRAINING_AMBASSADOR_TEMPLATE)


@require_POST
def create_training_ambassador(request):
    pro = _current_pro(request)
    form = TrainingAmbassadorForm(data=request.POST, pro=pro)
    if not form.is_valid():
        return _reject_engagement_form(request, form, pro, TRAINING_AMBASSADOR_TEMPLATE)

    pro = form.save(commit=False)
    already_exists = pro.pk is not None
    pro.add_engagement(Pro.Engagement.TRAINING_AMBASSADOR)
    pro.save()
    training_experience = form.after_save(pro)
    ConsortiumMailer.training_ambassador_signed_up(
        pro=pro, training_experience=training_experience
    )
    report_missing_record(form, pro, "Ambassadrice étudiante")
    _mail_pro_about_engagement(pro, already_exists)
    ProMailer.welcome_training_ambassador(pro=pro)
    return redirect("coalition_welcome")


def new_sponsor(request):
    return _render_engagement_form(request, EngagementForm, SPONSOR_TEMPLATE)


@require_POST
def create_sponsor(request):
    return _create_engagement(
        request,
        form_class=EngagementForm,
        engagement=Pro.Engagement.SPONSOR,
        template=SPONSOR_TEMPLATE,
    )


def new_internship(request):
    return render(request, "coalition/new_internship.html", {})


def new_workshop_request(request):
    return _render_engagement_form(request, WorkshopForm, WORKSHOP_TEMPLATE)


@require_POST
def create_workshop_request(request):
    pro = _current_pro(request)
    form = WorkshopForm(data=request.POST, pro=pro)
    if not form.is_valid():
        return _reject_engagement_form(request, form, pro, WORKSHOP_TEMPLATE)

    pro = form.save(commit=False)
    already_exists = pro.pk is not None
    pro.add_engagement(Pro.Engagement.WORKSHOPS)
    pro.save()
    for atelier in form.cleaned_data["ateliers"]:
        WorkshopRequest.objects.create(pro=pro, type=atelier, remark=form.cleaned_data["remark"])
    notify_workshop_request_task.delay(
        pro_pk=str(pro.pk),
        ateliers=form.cleaned_data["ateliers"],
        remark=form.cleaned_data["remark"],
        structure_uai=form.cleaned_data["structure_uai"],
    )
    report_missing_record(form, pro, "Demande d'atelier")
    _mail_pro_about_engagement(pro, already_exists)
    return redirect("coalition_welcome")


def new_manifeste_signature(request):
    return render(request, MANIFESTE_TEMPLATE, {"form": ManifesteSignatureForm()})


@require_POST
def create_manifeste_signature(request):
    form = ManifesteSignatureForm(data=request.POST)
    if not form.is_valid():
        _render_errors(request, form)
        return render(request, MANIFESTE_TEMPLATE, {"form": form})

    if settings.BREVO_SYNC_ENABLED:
        upsert_manifeste_signatory_task.delay(
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            email=form.cleaned_data["email"],
            structure_name=form.cleaned_data["structure_name"],
        )
    return redirect("show_manifeste_signature")


def show_manifeste_signature(request):
    manifeste_url = f"{settings.SITE_URL}/notre-manifeste/"
    return render(
        request,
        "coalition/show_manifeste_signature.html",
        {
            "linkedin_share_url": f"https://www.linkedin.com/sharing/share-offsite/?url={manifeste_url}"
        },
    )


def coalition_welcome(request):
    return render(request, "coalition/coalition_welcome.html", {})


# ------------------- private -------------------


def _current_pro(request):
    return request.user.pro if hasattr(request.user, "pro") else None


def _render_engagement_form(request, form_class, template):
    pro = _current_pro(request)
    return render(request, template, {"form": form_class(pro=pro), "pro": pro})


def _reject_engagement_form(request, form, pro, template):
    _render_errors(request, form)
    return render(request, template, {"form": form, "pro": pro})


def _create_engagement(request, *, form_class, engagement, template):
    pro = _current_pro(request)
    form = form_class(data=request.POST, pro=pro)
    if not form.is_valid():
        return _reject_engagement_form(request, form, pro, template)

    pro = form.save(commit=False)
    already_exists = pro.pk is not None
    pro.add_engagement(engagement)
    pro.save()
    ConsortiumMailer.pro_signed_up(pro=pro, engagement=engagement)
    _mail_pro_about_engagement(pro, already_exists)
    return redirect("coalition_welcome")


def _mail_pro_about_engagement(pro, already_exists):
    if already_exists:
        ProMailer.engagement_added(pro=pro)
    else:
        ProMailer.welcome(pro=pro, token=pro.issue_login_token())


def _render_errors(request, form):
    if form.has_error("email", "email_exists"):
        messages.error(
            request,
            "Un compte existe déjà pour cette adresse mail, merci de vous connecter "
            "avant de soumettre votre engagement.",
        )
    else:
        messages.error(
            request,
            "Des erreurs empêchent la validation du formulaire, "
            "merci de les corriger et de réessayer à nouveau.",
        )
