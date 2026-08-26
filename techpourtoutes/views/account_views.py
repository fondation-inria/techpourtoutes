from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from techpourtoutes.services.account.soft_delete_account import SoftDeleteAccount

from ..forms import (
    BeneficiaryEditAccountForm,
    CommunicationForm,
    DeleteAccountForm,
    EmailChangeForm,
    ProEditAccountForm,
    VerificationCodeForm,
)
from ..mailers import AuthMailer
from ..ratelimit import rate_limit
from ..services.account.verify_email_change_code import VerifyEmailChangeCode
from ..utils.text import mask_email
from ..utils.training_experience import training_experience_slots


@login_required
def account(request):
    is_pro, is_beneficiary, user = _resolve_account(request)
    context = {"user": user, "is_pro": is_pro, "is_beneficiary": is_beneficiary}
    return render(request, "account/account.html", context)


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
def account_detail(request):
    is_pro, is_beneficiary, user = _resolve_account(request)
    form = CommunicationForm(user=user)
    context = {"user": user, "is_pro": is_pro, "is_beneficiary": is_beneficiary, "form": form}
    if is_beneficiary:
        context["training_experience_slots"] = training_experience_slots(
            user.training_experiences.all()
        )
    return render(
        request,
        "account/partials/account_detail.html",
        context,
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
            "La demande de changement d'adresse a expiré. Veuillez recommencer.",
        )
        return redirect("account")

    form = VerificationCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = VerifyEmailChangeCode(user=user, payload=payload, code=form.cleaned_data["code"])
        if result.success:
            if payload["stage"] == "new":
                messages.success(request, "L'adresse mail a bien été modifiée.")
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
            "La demande de changement d'adresse a expiré. Veuillez recommencer.",
        )
        return redirect("account")

    stage, new_email = payload["stage"], payload["new_email"]
    recipient = new_email if stage == "new" else user.email
    AuthMailer.change_email(user=user, code=user.set_email_change_code(), new_email=recipient)
    messages.success(request, "Un nouveau code a été envoyé par mail.")
    return redirect(user.email_change_verify_url(user.issue_email_change_token(new_email, stage)))


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
