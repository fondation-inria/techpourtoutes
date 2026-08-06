import uuid

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from techpourtoutes.services.soft_delete_account import SoftDeleteAccount

from ..forms import (
    BeneficiaryEditAccountForm,
    BeneficiaryTrainingExperienceForm,
    CommunicationForm,
    DeleteAccountForm,
    EmailChangeForm,
    ProEditAccountForm,
    ProTrainingExperienceForm,
    VerificationCodeForm,
)
from ..mailers import AuthMailer
from ..models import TrainingExperience
from ..models.training_experience import training_experience_insertion_anchor
from ..ratelimit import rate_limit
from ..services.verify_email_change_code import VerifyEmailChangeCode
from ..utils.text import mask_email


@login_required
def account(request):
    is_pro, is_beneficiary, user = _resolve_account(request)
    form = CommunicationForm(user=user)
    return render(
        request,
        "account/account.html",
        {"user": user, "is_pro": is_pro, "is_beneficiary": is_beneficiary, "form": form},
    )


@require_POST
@login_required
def account_communication(request):
    _is_pro, _is_beneficiary, user = _resolve_account(request)
    form = CommunicationForm(data=request.POST, user=user)
    if form.is_valid():
        form.save(user)
    return render(
        request,
        "account/partials/communication_card.html",
        {"user": user, "form": form},
    )


@login_required
def account_info(request):
    is_pro, is_beneficiary, user = _resolve_account(request)
    return render(
        request,
        "account/partials/info_card.html",
        {"user": user, "is_pro": is_pro, "is_beneficiary": is_beneficiary},
    )


@login_required
def account_edit(request):
    is_pro, is_beneficiary, user = _resolve_account(request)

    form_class = ProEditAccountForm if is_pro else BeneficiaryEditAccountForm
    form_kwarg = "pro" if is_pro else "beneficiary"

    form = form_class(**{form_kwarg: user})
    if request.method == "POST":
        form = form_class(data=request.POST, **{form_kwarg: user})
        if form.is_valid():
            form.save(user)
            return render(
                request,
                "account/partials/info_card.html",
                {"user": user, "is_pro": is_pro, "is_beneficiary": is_beneficiary},
            )
    return render(
        request,
        "account/partials/edit_form.html",
        {"form": form, "user": user, "is_pro": is_pro, "is_beneficiary": is_beneficiary},
    )


@login_required
def account_email(request):
    user = request.user.pro if hasattr(request.user, "pro") else request.user
    return render(request, "account/partials/email_section.html", {"user": user})


@login_required
def email_change(request):
    user = request.user.pro if hasattr(request.user, "pro") else request.user
    if request.method == "POST":
        form = EmailChangeForm(request.POST, user=user)
        if form.is_valid():
            AuthMailer.change_email(user=user, code=user.set_email_change_code())
            token = user.issue_email_change_token(form.cleaned_data["email"], "current")
            return HttpResponse(headers={"HX-Redirect": user.email_change_verify_url(token)})
    else:
        form = EmailChangeForm(user=user)
    return render(
        request,
        "account/partials/email_section.html",
        {"form": form, "user": user, "editing": True},
    )


@login_required
def email_change_verify(request):
    user = request.user.pro if hasattr(request.user, "pro") else request.user
    token = request.POST.get("token") or request.GET.get("token", "")
    payload = user.read_email_change_token(token)
    if payload is None:
        messages.error(
            request,
            "Votre demande de changement d'adresse a expiré. Veuillez recommencer.",
        )
        return redirect("account")

    form = VerificationCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = VerifyEmailChangeCode(user=user, payload=payload, code=form.cleaned_data["code"])
        if result.success:
            if payload["stage"] == "new":
                messages.success(request, "Votre adresse mail a été modifiée.")
            return redirect(result.redirect_url)
        form.add_error("code", result.errors[0])

    recipient = user.email if payload["stage"] == "current" else payload["new_email"]
    return render(
        request,
        "account/email_change_verify.html",
        {
            "form": form,
            "token": token,
            "stage": payload["stage"],
            "masked_recipient": mask_email(recipient),
        },
    )


@require_POST
@login_required
@rate_limit("RATELIMIT_EMAIL_CHANGE_RESEND")
def email_change_resend(request):
    user = request.user.pro if hasattr(request.user, "pro") else request.user
    payload = user.read_email_change_token(request.POST.get("token", ""))
    if payload is None:
        messages.error(
            request,
            "Votre demande de changement d'adresse a expiré. Veuillez recommencer.",
        )
        return redirect("account")

    stage, new_email = payload["stage"], payload["new_email"]
    recipient = new_email if stage == "new" else user.email
    AuthMailer.change_email(user=user, code=user.set_email_change_code(), new_email=recipient)
    messages.success(request, "Un nouveau code vous a été envoyé par mail.")
    return redirect(user.email_change_verify_url(user.issue_email_change_token(new_email, stage)))


@login_required
def pro_training_experience_info(request, pk):
    experience = _get_pro_training_experience(request, pk)
    return render(
        request,
        "account/partials/pro_training_experience_card.html",
        {"experience": experience},
    )


@login_required
def pro_training_experience_edit(request, pk):
    experience = _get_pro_training_experience(request, pk)
    if request.method == "POST":
        form = ProTrainingExperienceForm(data=request.POST)
        if form.is_valid():
            form.save(experience)
            return render(
                request,
                "account/partials/pro_training_experience_card.html",
                {"experience": experience},
            )
    else:
        form = ProTrainingExperienceForm(experience=experience)
    return render(
        request,
        "account/partials/pro_training_experience_edit_form.html",
        {"form": form, "experience": experience},
    )


@login_required
def beneficiary_training_experience_form(request, pk=None):
    beneficiary = None
    experience = None
    if pk is None:
        beneficiary = _get_beneficiary(request)
    else:
        experience = _get_beneficiary_training_experience(request, pk)

    if request.method == "POST":
        if experience is None:
            prefix = request.POST.get("form_prefix")
            is_new_current_year = prefix == "current-year"
        else:
            prefix = str(experience.pk)
            is_new_current_year = False
        form = BeneficiaryTrainingExperienceForm(
            data=request.POST,
            beneficiary=beneficiary,
            experience=experience,
            current_year=is_new_current_year,
            prefix=prefix,
        )
        if form.is_valid():
            if form.cleaned_data.get("not_enrolled"):
                if experience is not None:
                    rejection = _reject_last_training_experience(request, experience)
                    if rejection:
                        return rejection
                    experience.delete()
                return _render_beneficiary_training_experience_item(request, experience=None)
            saved = form.save(experience or TrainingExperience(user=beneficiary))
            return _render_beneficiary_training_experience_item(
                request, saved, oob_swap=_training_experience_oob_swap(saved)
            )
    elif experience is None:
        is_new_current_year = request.GET.get("current_year") == "true"
        prefix = "current-year" if is_new_current_year else uuid.uuid4().hex
        form = BeneficiaryTrainingExperienceForm(
            beneficiary=beneficiary, current_year=is_new_current_year, prefix=prefix
        )
    else:
        is_new_current_year = False
        form = BeneficiaryTrainingExperienceForm(experience=experience, prefix=str(experience.pk))

    return render(
        request,
        "account/partials/beneficiary_training_experience_edit_form.html",
        {"form": form, "experience": experience, "current_year": is_new_current_year},
    )


@login_required
def beneficiary_training_experience_info(request, pk):
    experience = _get_beneficiary_training_experience(request, pk)
    return _render_beneficiary_training_experience_item(request, experience)


@require_POST
@login_required
def beneficiary_training_experience_delete(request, pk):
    experience = _get_beneficiary_training_experience(request, pk)
    if experience.is_current_school_year:
        return HttpResponseForbidden()
    rejection = _reject_last_training_experience(request, experience)
    if rejection:
        return rejection
    experience.delete()
    return HttpResponse()


@login_required
def delete_account_modal(request):
    form = DeleteAccountForm()
    return render(
        request,
        "account/partials/delete_account_modal.html",
        {"form": form, "is_pro": hasattr(request.user, "pro")},
    )


@require_POST
@login_required
def delete_account(request):
    _is_pro, _is_beneficiary, user = _resolve_account(request)
    form = DeleteAccountForm(request.POST)
    if form.is_valid():
        result = SoftDeleteAccount(user=user)
        if result.failure:
            for error in result.errors:
                messages.error(request, error)
            return render(
                request,
                "account/partials/delete_account_modal.html",
                {"form": form},
            )
        logout(request)
        messages.success(request, "Le compte a bien été supprimé.")
        return HttpResponse(headers={"HX-Redirect": "/"})
    return render(
        request,
        "account/partials/delete_account_modal.html",
        {"form": form},
    )


# --------------------- private ----------------


def _resolve_account(request):
    is_pro = hasattr(request.user, "pro")
    is_beneficiary = hasattr(request.user, "beneficiary")
    if is_pro:
        user = request.user.pro
    elif is_beneficiary:
        user = request.user.beneficiary
    else:
        user = request.user
    return is_pro, is_beneficiary, user


def _get_pro_training_experience(request, pk):
    if not hasattr(request.user, "pro"):
        raise Http404
    return get_object_or_404(request.user.pro.training_experiences, pk=pk)


def _render_beneficiary_training_experience_item(request, experience, oob_swap=None):
    return render(
        request,
        "account/partials/beneficiary_training_experience_item.html",
        {"experience": experience, "oob_swap": oob_swap},
    )


def _training_experience_oob_swap(experience):
    anchor = training_experience_insertion_anchor(
        experience.user, experience.start_date, exclude_pk=experience.pk
    )
    if anchor is None:
        return "beforeend:#beneficiary-training-experiences"
    return f"beforebegin:#beneficiary-training-experience-{anchor}"


def _get_beneficiary(request):
    if not hasattr(request.user, "beneficiary"):
        raise Http404
    return request.user.beneficiary


def _get_beneficiary_training_experience(request, pk):
    if not hasattr(request.user, "beneficiary"):
        raise Http404
    return get_object_or_404(request.user.beneficiary.training_experiences, pk=pk)


def _reject_last_training_experience(request, experience):
    if _has_other_training_experience(experience):
        return None
    messages.error(request, "Au moins une formation doit être renseignée.")
    return HttpResponse(headers={"HX-Redirect": reverse("account")})


def _has_other_training_experience(experience):
    return experience.user.training_experiences.exclude(pk=experience.pk).exists()
