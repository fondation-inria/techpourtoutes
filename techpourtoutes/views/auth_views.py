from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from techpourtoutes.services.soft_delete_account import SoftDeleteAccount

from ..forms import (
    AccountEditForm,
    CommunicationForm,
    DeleteAccountForm,
    EmailChangeForm,
    LoginRequestForm,
    TrainingExperienceForm,
    VerificationCodeForm,
)
from ..mailers import AuthMailer
from ..models.user import LOGIN_CODE_MAX_ATTEMPTS
from ..ratelimit import rate_limit
from ..services.jobirl_api.refresh_access_token import RefreshAccessToken
from ..services.verify_email_change_code import VerifyEmailChangeCode
from ..text import mask_email


@rate_limit("RATELIMIT_LOGIN", keys=("email",))
def login_request(request):
    if request.user.is_authenticated:
        return redirect(reverse("account"))

    if request.method == "POST":
        form = LoginRequestForm(data=request.POST)
        next_url = _safe_next(request, request.POST.get(REDIRECT_FIELD_NAME, ""))
        back_url = _safe_next(request, request.POST.get("back", ""))
        if form.is_valid():
            email = form.cleaned_data["email"]
            User = get_user_model()
            user = User.objects.filter(email=email, is_active=True).first()
            if user is not None:
                AuthMailer.login_code(user=user, code=user.issue_login_code())
            request.session["login_email"] = email
            request.session["login_next"] = next_url

            url = reverse("login_code")
            if back_url:
                url = f"{url}?{urlencode({'back': back_url})}"

            referer = request.headers.get("referer", "")
            if referer.startswith(settings.SITE_URL) and urlparse(referer).path == reverse(
                "login_code"
            ):
                messages.success(request, "Un nouveau code vous a été envoyé par mail.")
            return redirect(url)
    else:
        form = LoginRequestForm()
        next_url = _safe_next(request, request.GET.get(REDIRECT_FIELD_NAME, ""))
        back_url = _safe_next(request, request.GET.get("back", ""))

    return render(
        request,
        "registration/login_request.html",
        {"form": form, "next": next_url, "back": back_url},
    )


def login_code(request):
    if request.user.is_authenticated:
        return redirect(reverse("account"))
    email = request.session.get("login_email")
    if not email:
        return redirect("login_request")
    back_url = _safe_next(request, request.GET.get("back", ""))
    next_url = _safe_next(request, request.session.get("login_next", ""))
    User = get_user_model()
    user = User.objects.filter(email=email, is_active=True).first()

    form = VerificationCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if user is not None and user.verify_login_code(form.cleaned_data["code"]):
            user.clear_login_code()
            request.session.pop("login_email", None)
            request.session.pop("login_next", None)
            # the following line required because django-axes is configured
            user.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user)
            messages.success(request, f"Vous accédez au compte {user.email}. Bienvenue !")
            return redirect(next_url or reverse("account"))
        if user is not None and user.login_code_attempts >= LOGIN_CODE_MAX_ATTEMPTS:
            user.clear_login_code()
        form.add_error("code", "Code invalide ou expiré.")

    return render(
        request,
        "registration/login_code.html",
        {
            "form": form,
            "email": email,
            "masked_recipient": mask_email(email),
            "back": back_url,
        },
    )


def login_verify(request, token):
    if request.user.is_authenticated:
        logout(request)
    next_url = _safe_next(request, request.GET.get(REDIRECT_FIELD_NAME, ""))
    User = get_user_model()
    user = User.consume_login_token(plaintext=token)
    if user is None:
        messages.error(
            request,
            "Ce lien est invalide ou a expiré - sa durée est d'une heure maximum. "
            "Veuillez en demander un nouveau.",
        )
        target = reverse("login_request")
        if next_url:
            target = f"{target}?{urlencode({'next': next_url})}"
        return redirect(target)

    # the following line required because django-axes is configured
    user.backend = "django.contrib.auth.backends.ModelBackend"
    login(request, user)
    messages.success(request, f"Vous accédez au compte {user.email}. Bienvenue !")
    return redirect(next_url or reverse("account"))


@login_required
def login_to_jobirl(request):
    if not hasattr(request.user, "pro"):
        messages.error(request, "Vous n'avez pas de compte mentor sur JobIRL")
        form = CommunicationForm(pro=request.user)
        return render(request, "account/account.html", {"form": form})

    result = RefreshAccessToken(pro=request.user.pro)
    if result.failure:
        messages.error(request, result.errors[0])
        return redirect(reverse("account"))

    return redirect(f"{settings.JOBIRL_URL}/techpourtoutes/auth/{result.token}")


@login_required
def account(request):
    user = request.user.pro if hasattr(request.user, "pro") else request.user
    form = CommunicationForm(pro=user)
    return render(request, "account/account.html", {"user": user, "form": form})


@require_POST
@login_required
def account_communication(request):
    pro = request.user.pro
    form = CommunicationForm(data=request.POST, pro=pro)
    if form.is_valid():
        form.save(pro)
    return render(
        request,
        "account/partials/communication_card.html",
        {"user": pro, "form": form},
    )


@login_required
def account_info(request):
    user = request.user.pro if hasattr(request.user, "pro") else request.user
    return render(request, "account/partials/info_card.html", {"user": user})


@login_required
def account_edit(request):
    pro = request.user.pro
    if request.method == "POST":
        form = AccountEditForm(data=request.POST, pro=pro)
        if form.is_valid():
            form.save(pro)
            return render(request, "account/partials/info_card.html", {"user": pro})
        return render(request, "account/partials/edit_form.html", {"form": form, "user": pro})
    else:
        form = AccountEditForm(pro=pro)
        return render(request, "account/partials/edit_form.html", {"form": form, "user": pro})


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
def training_experience_info(request, pk):
    experience = _get_training_experience(request, pk)
    return render(
        request,
        "account/partials/training_experience_card.html",
        {"experience": experience},
    )


@login_required
def training_experience_edit(request, pk):
    experience = _get_training_experience(request, pk)
    if request.method == "POST":
        form = TrainingExperienceForm(data=request.POST)
        if form.is_valid():
            form.save(experience)
            return render(
                request,
                "account/partials/training_experience_card.html",
                {"experience": experience},
            )
    else:
        form = TrainingExperienceForm(experience=experience)
    return render(
        request,
        "account/partials/training_experience_edit_form.html",
        {"form": form, "experience": experience},
    )


@require_POST
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Au revoir - Déconnexion réalisée avec succès")
    return redirect("/")


@login_required
def delete_account_modal(request):
    form = DeleteAccountForm()
    return render(request, "account/partials/delete_account_modal.html", {"form": form})


@require_POST
@login_required
def delete_account(request):
    user = request.user.pro if hasattr(request.user, "pro") else request.user
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
        messages.success(request, "Votre compte a été supprimé.")
        return HttpResponse(headers={"HX-Redirect": "/"})
    return render(
        request,
        "account/partials/delete_account_modal.html",
        {"form": form},
    )


# --------------------- private ----------------


def _get_training_experience(request, pk):
    return get_object_or_404(request.user.pro.training_experiences, pk=pk)


def _safe_next(request, candidate):
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ""
