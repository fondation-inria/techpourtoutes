from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..forms import LoginRequestForm
from ..mailers import LoginMailer


def _safe_next(request, candidate):
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ""


def login_request(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == "POST":
        form = LoginRequestForm(data=request.POST)
        next_url = _safe_next(request, request.POST.get(REDIRECT_FIELD_NAME, ""))
        if form.is_valid():
            email = form.cleaned_data["email"]
            User = get_user_model()
            user = User.objects.filter(email=email, is_active=True).first()
            if user is not None:
                plaintext = user.issue_login_token()
                LoginMailer.send_link(user=user, token=plaintext, next_url=next_url)
            request.session["login_email"] = email
            return redirect("login_email_sent")
    else:
        form = LoginRequestForm()
        next_url = _safe_next(request, request.GET.get(REDIRECT_FIELD_NAME, ""))

    return render(
        request,
        "registration/login_request.html",
        {"form": form, "next": next_url},
    )


def login_email_sent(request):
    email = request.session.get("login_email")
    if not email:
        return redirect("login_request")
    return render(request, "registration/login_email_sent.html", {"email": email})


def login_verify(request, token):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    next_url = _safe_next(request, request.GET.get(REDIRECT_FIELD_NAME, ""))
    User = get_user_model()
    user = User.consume_login_token(plaintext=token)
    if user is None:
        messages.error(
            request,
            "Ce lien est invalide ou a expiré. Veuillez en demander un nouveau.",
        )
        target = reverse("login_request")
        if next_url:
            target = f"{target}?{urlencode({'next': next_url})}"
        return redirect(target)

    login(request, user)
    messages.success(request, f"Vous accédez au compte {user.email}. Bienvenue !")
    return redirect(next_url or settings.LOGIN_REDIRECT_URL)


@login_required
def account(request):
    return render(request, "account/account.html", {})


@require_POST
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Au revoir - Déconnexion réalisée avec succès")
    return redirect("/")
