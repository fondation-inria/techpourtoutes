from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render

from ..forms import EngagementForm, ManifesteSignatureForm, TrainingAmbassadorForm, WorkshopForm
from ..mailers import CoalitionInternalMailer, CoalitionUserMailer
from ..models import Pro, WorkshopRequest
from ..services.create_mentor import CreateMentor
from ..tasks import notify_workshop_request_task, upsert_manifeste_signatory_task


def coalition_home(request):
    return render(request, "coalition/coalition_home.html", {})


def mentor_landing(request):
    pro = _current_pro(request)
    if request.method == "POST":
        form = EngagementForm(data=request.POST, pro=pro)
        if form.is_valid():
            result = CreateMentor(pro=form.save(commit=False))
            if result.failure:
                for error in result.errors:
                    messages.error(request, error)
                return render(request, "coalition/mentor_landing.html", {"form": form, "pro": pro})
            return redirect("coalition_welcome")
        else:
            _render_errors(request, form)
    else:
        form = EngagementForm(pro=pro)
    return render(request, "coalition/mentor_landing.html", {"form": form, "pro": pro})


def work_ambassador_landing(request):
    return _handle_engagement(
        request,
        form_class=EngagementForm,
        engagement=Pro.Engagement.WORK_AMBASSADOR,
        template="coalition/work_ambassador_landing.html",
    )


def training_ambassador_landing(request):
    pro = _current_pro(request)
    if request.method == "POST":
        form = TrainingAmbassadorForm(data=request.POST, pro=pro)
        if form.is_valid():
            pro = form.save(commit=False)
            already_exists = pro.pk is not None
            pro.add_engagement(Pro.Engagement.TRAINING_AMBASSADOR)
            pro.save()
            training_experience = form.after_save(pro)
            CoalitionInternalMailer.new_training_ambassador(
                pro=pro, training_experience=training_experience
            )
            if already_exists:
                CoalitionUserMailer.new_engagement(pro=pro)
            else:
                CoalitionUserMailer.welcome(pro=pro, token=pro.issue_login_token())
            return redirect("coalition_welcome")
        else:
            _render_errors(request, form)
    else:
        form = TrainingAmbassadorForm(pro=pro)
    return render(
        request, "coalition/training_ambassador_landing.html", {"form": form, "pro": pro}
    )


def sponsor_landing(request):
    return _handle_engagement(
        request,
        form_class=EngagementForm,
        engagement=Pro.Engagement.SPONSOR,
        template="coalition/sponsor_landing.html",
    )


def internships_landing(request):
    return render(request, "coalition/internships_landing.html", {})


def workshops_landing(request):
    pro = _current_pro(request)
    if request.method == "POST":
        form = WorkshopForm(data=request.POST, pro=pro)
        if form.is_valid():
            pro = form.save(commit=False)
            already_exists = pro.pk is not None
            pro.add_engagement(Pro.Engagement.WORKSHOPS)
            pro.save()
            for atelier in form.cleaned_data["ateliers"]:
                WorkshopRequest.objects.create(
                    pro=pro, type=atelier, remark=form.cleaned_data["remark"]
                )
            notify_workshop_request_task.delay(
                str(pro.pk), form.cleaned_data["ateliers"], form.cleaned_data["remark"]
            )
            if already_exists:
                CoalitionUserMailer.new_engagement(pro=pro)
            else:
                CoalitionUserMailer.welcome(pro=pro, token=pro.issue_login_token())
            return redirect("coalition_welcome")
        else:
            _render_errors(request, form)
    else:
        form = WorkshopForm(pro=pro)
    return render(request, "coalition/workshops_landing.html", {"form": form, "pro": pro})


def signer_manifeste(request):
    if request.method == "POST":
        form = ManifesteSignatureForm(data=request.POST)
        if form.is_valid():
            if settings.BREVO_SYNC_ENABLED:
                upsert_manifeste_signatory_task.delay(
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    email=form.cleaned_data["email"],
                    structure_name=form.cleaned_data["structure_name"],
                )
            return redirect("signature_manifeste")
        _render_errors(request, form)
    else:
        form = ManifesteSignatureForm()
    return render(request, "static/signer_manifeste.html", {"form": form})


def coalition_welcome(request):
    return render(request, "coalition/coalition_welcome.html", {})


# ------------------- private -------------------


def _current_pro(request):
    return request.user.pro if hasattr(request.user, "pro") else None


def _handle_engagement(request, *, form_class, engagement, template):
    pro = _current_pro(request)
    if request.method == "POST":
        form = form_class(data=request.POST, pro=pro)
        if form.is_valid():
            pro = form.save(commit=False)
            already_exists = pro.pk is not None
            pro.add_engagement(engagement)
            pro.save()
            CoalitionInternalMailer.new_pro(pro=pro, engagement=engagement)
            if already_exists:
                CoalitionUserMailer.new_engagement(pro=pro)
            else:
                CoalitionUserMailer.welcome(pro=pro, token=pro.issue_login_token())
            return redirect("coalition_welcome")
        else:
            _render_errors(request, form)
    else:
        form = form_class(pro=pro)
    return render(request, template, {"form": form, "pro": pro})


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
