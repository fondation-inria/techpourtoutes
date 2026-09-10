from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from techpourtoutes.services.account.soft_delete_user import SoftDeleteUser

from ..forms import (
    BeneficiaryEditAccountForm,
    DeleteAccountForm,
    EmailChangeForm,
    ProEditAccountForm,
    UserCommunicationForm,
    VerificationCodeForm,
)
from ..mailers import AuthMailer
from ..ratelimit import rate_limit
from ..services.account.verify_email_change_code import VerifyEmailChangeCode
from ..utils.text import mask_email
from ..utils.training_experience import training_experience_slots


@login_required
def show_account(request):
    is_pro, is_beneficiary, user = _resolve_user(request)
    context = {"user": user, "is_pro": is_pro, "is_beneficiary": is_beneficiary}
    return render(request, "account/show_account.html", context)


@require_POST
@login_required
def update_user_communication(request):
    _is_pro, _is_beneficiary, user = _resolve_user(request)
    form = UserCommunicationForm(data=request.POST, user=user)
    if form.is_valid():
        form.save(user)
    return render(
        request,
        "account/partials/edit_user_communication.html",
        {"user": user, "form": form},
    )


@login_required
def show_user(request):
    is_pro, is_beneficiary, user = _resolve_user(request)
    form = UserCommunicationForm(user=user)
    context = {"user": user, "is_pro": is_pro, "is_beneficiary": is_beneficiary, "form": form}
    if is_beneficiary:
        context["training_experience_slots"] = training_experience_slots(
            user.training_experiences.all()
        )
    return render(
        request,
        "account/partials/show_user.html",
        context,
    )


@login_required
def show_user_info(request):
    is_pro, is_beneficiary, user = _resolve_user(request)
    return render(
        request,
        "account/partials/show_user_info.html",
        {"user": user, "is_pro": is_pro, "is_beneficiary": is_beneficiary},
    )


@login_required
def edit_user(request):
    is_pro, is_beneficiary, user = _resolve_user(request)
    form_class, form_kwarg = _user_form_for(is_pro)
    return _render_user_edit_form(request, form_class(**{form_kwarg: user}))


@require_POST
@login_required
def update_user(request):
    is_pro, is_beneficiary, user = _resolve_user(request)
    form_class, form_kwarg = _user_form_for(is_pro)

    form = form_class(data=request.POST, **{form_kwarg: user})
    if not form.is_valid():
        return _render_user_edit_form(request, form)

    form.save(user)
    return render(
        request,
        "account/partials/show_user_info.html",
        {"user": user, "is_pro": is_pro, "is_beneficiary": is_beneficiary},
    )


@login_required
def show_user_email(request):
    return render(
        request, "account/partials/edit_user_email.html", {"user": _current_user(request)}
    )


@login_required
def edit_user_email(request):
    user = _current_user(request)
    return _render_user_email_form(request, user, EmailChangeForm(user=user))


@require_POST
@login_required
def create_user_email_change(request):
    user = _current_user(request)
    form = EmailChangeForm(request.POST, user=user)
    if not form.is_valid():
        return _render_user_email_form(request, user, form)

    AuthMailer.change_email(user=user, code=user.set_email_change_code())
    token = user.issue_email_change_token(form.cleaned_data["email"], "current")
    return HttpResponse(headers={"HX-Redirect": user.update_email_verification_url(token)})


@login_required
def show_user_email_verification(request):
    user = _current_user(request)
    token = request.GET.get("token", "")
    payload = user.read_email_change_token(token)
    if payload is None:
        return _reject_expired_email_change(request)
    return _render_user_email_verification(request, user, token, payload, VerificationCodeForm())


@require_POST
@login_required
def update_user_email(request):
    user = _current_user(request)
    token = request.POST.get("token", "")
    payload = user.read_email_change_token(token)
    if payload is None:
        return _reject_expired_email_change(request)

    form = VerificationCodeForm(request.POST)
    if form.is_valid():
        result = VerifyEmailChangeCode(user=user, payload=payload, code=form.cleaned_data["code"])
        if result.success:
            if payload["stage"] == "new":
                messages.success(request, "L'adresse mail a bien été modifiée.")
            return redirect(result.redirect_url)
        form.add_error("code", result.errors[0])
    return _render_user_email_verification(request, user, token, payload, form)


@require_POST
@login_required
@rate_limit("RATELIMIT_EMAIL_CHANGE_RESEND")
def create_user_email_code(request):
    user = _current_user(request)
    payload = user.read_email_change_token(request.POST.get("token", ""))
    if payload is None:
        return _reject_expired_email_change(request)

    stage, new_email = payload["stage"], payload["new_email"]
    recipient = new_email if stage == "new" else user.email
    AuthMailer.change_email(user=user, code=user.set_email_change_code(), new_email=recipient)
    messages.success(request, "Un nouveau code a été envoyé par mail.")
    return redirect(
        user.update_email_verification_url(user.issue_email_change_token(new_email, stage))
    )


@login_required
def destroy_user_modal(request):
    form = DeleteAccountForm()
    return render(
        request,
        "account/partials/destroy_user_modal.html",
        {"form": form, "is_pro": hasattr(request.user, "pro")},
    )


@require_POST
@login_required
def destroy_user(request):
    _is_pro, _is_beneficiary, user = _resolve_user(request)
    form = DeleteAccountForm(request.POST)
    if form.is_valid():
        result = SoftDeleteUser(user=user)
        if result.failure:
            for error in result.errors:
                messages.error(request, error)
            return render(
                request,
                "account/partials/destroy_user_modal.html",
                {"form": form},
            )
        logout(request)
        messages.success(request, "Le compte a bien été supprimé.")
        return HttpResponse(headers={"HX-Redirect": "/"})
    return render(
        request,
        "account/partials/destroy_user_modal.html",
        {"form": form},
    )


# --------------------- private ----------------


def _current_user(request):
    return request.user.pro if hasattr(request.user, "pro") else request.user


def _user_form_for(is_pro):
    if is_pro:
        return ProEditAccountForm, "pro"
    return BeneficiaryEditAccountForm, "beneficiary"


def _render_user_edit_form(request, form):
    is_pro, is_beneficiary, user = _resolve_user(request)
    return render(
        request,
        "account/partials/edit_user.html",
        {"form": form, "user": user, "is_pro": is_pro, "is_beneficiary": is_beneficiary},
    )


def _render_user_email_form(request, user, form):
    return render(
        request,
        "account/partials/edit_user_email.html",
        {"form": form, "user": user, "editing": True},
    )


def _reject_expired_email_change(request):
    messages.error(
        request,
        "La demande de changement d'adresse a expiré. Veuillez recommencer.",
    )
    return redirect("show_account")


def _render_user_email_verification(request, user, token, payload, form):
    recipient = user.email if payload["stage"] == "current" else payload["new_email"]
    return render(
        request,
        "account/show_user_email_verification.html",
        {
            "form": form,
            "token": token,
            "stage": payload["stage"],
            "masked_recipient": mask_email(recipient),
        },
    )


def _resolve_user(request):
    is_pro = hasattr(request.user, "pro")
    is_beneficiary = hasattr(request.user, "beneficiary")
    if is_pro:
        user = request.user.pro
    elif is_beneficiary:
        user = request.user.beneficiary
    else:
        user = request.user
    return is_pro, is_beneficiary, user
