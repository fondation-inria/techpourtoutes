from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..forms import CommunicationForm, LoginRequestForm, VerificationCodeForm
from ..mailers import AuthMailer
from ..models import User
from ..ratelimit import rate_limit
from ..services.jobirl_api.refresh_access_token import RefreshAccessToken
from ..utils.text import mask_email


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
                messages.success(request, "Un nouveau code a été envoyé par mail.")
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
    user = User.objects.filter(email=email, is_active=True).first()

    form = VerificationCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if user is not None and user.consume_login_code(form.cleaned_data["code"]):
            request.session.pop("login_email", None)
            request.session.pop("login_next", None)
            # the following line required because django-axes is configured
            user.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user)
            messages.success(request, f"Bienvenue sur le compte {user.email} !")
            return redirect(next_url or reverse("account"))
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
        form = CommunicationForm(user=request.user)
        return render(request, "account/account.html", {"form": form})

    result = RefreshAccessToken(pro=request.user.pro)
    if result.failure:
        messages.error(request, result.errors[0])
        return redirect(reverse("account"))

    return redirect(f"{settings.JOBIRL_URL}/techpourtoutes/auth/{result.token}")


@require_POST
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Au revoir - Déconnexion réalisée avec succès")
    return redirect("/")


# --------------------- private ----------------


def _safe_next(request, candidate):
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ""
