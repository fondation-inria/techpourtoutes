from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from techpourtoutes.forms.delete_account_form import DeleteAccountForm
from techpourtoutes.mailers.coalition_internal_mailer import CoalitionInternalMailer
from techpourtoutes.mailers.coalition_user_mailer import CoalitionUserMailer

from ..forms import (
    AccountEditForm,
    CommunicationForm,
    LoginRequestForm,
    TrainingExperienceForm,
)
from ..mailers import AuthMailer
from ..ratelimit import rate_limit
from ..services.jobirl_api.refresh_access_token import RefreshAccessToken


def _safe_next(request, candidate):
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ""


@rate_limit("RATELIMIT_LOGIN", keys=("email",))
def login_request(request):
    if request.user.is_authenticated:
        return redirect(reverse("account"))

    if request.method == "POST":
        form = LoginRequestForm(data=request.POST)
        next_url = _safe_next(request, request.POST.get(REDIRECT_FIELD_NAME, ""))
        if form.is_valid():
            email = form.cleaned_data["email"]
            User = get_user_model()
            user = User.objects.filter(email=email, is_active=True).first()
            if user is not None:
                token = user.issue_login_token()
                AuthMailer.login_link(user=user, token=token, next_url=next_url)
            request.session["login_email"] = email
            email_sent_url = f"{settings.SITE_URL}{reverse('login_email_sent')}"
            if request.headers.get("referer") == email_sent_url:
                messages.success(request, "Votre demande a bien été prise en compte.")
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
    if not hasattr(request.user, "pro"):
        return redirect("account")
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
    if not hasattr(request.user, "pro"):
        return redirect("account")
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


def _get_training_experience(request, pk):
    if not hasattr(request.user, "pro"):
        raise Http404
    return get_object_or_404(request.user.pro.training_experiences, pk=pk)


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
        recipient_email = user.email
        first_name = user.first_name
        last_name = user.last_name
        engagements = user.engagements
        jobirl_id = user.jobirl_user_id
        user.deactivate_user()
        user.save()
        logout(request)
        CoalitionUserMailer.delete_account(
            recipient_email=recipient_email, first_name=first_name, engagements=engagements
        )
        CoalitionInternalMailer.delete_account_request(
            first_name=first_name, last_name=last_name, jobirl_id=jobirl_id
        )
        messages.success(request, "Votre compte a été supprimé.")
        return HttpResponse('<script>window.location = "/";</script>')
    return render(
        request,
        "account/partials/delete_account_modal.html",
        {"form": form},
    )
