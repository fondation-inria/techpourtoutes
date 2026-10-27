from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..forms import LegalRepresentativeAuthorizationForm
from ..models import LegalRepresentativeAuthorization
from ..ratelimit import client_ip
from ..services.legal_representative_authorization.sign_authorization import (
    SignLegalRepresentativeAuthorization,
)


def show_legal_representative_authorization(request, token):
    """Once signed, thanks the signatory; a link the beneficiary since replaced, or never was,
    says it is no longer valid."""
    authorization = _find(token)
    if authorization and not _is_signed(authorization):
        return redirect("edit_legal_representative_authorization", token=token)
    return render(
        request,
        "legal_representative_authorization/show_legal_representative_authorization.html",
        {"authorization": authorization},
    )


def edit_legal_representative_authorization(request, token):
    authorization = _find(token)
    if not authorization or _is_signed(authorization):
        return redirect("show_legal_representative_authorization", token=token)
    form = LegalRepresentativeAuthorizationForm(
        initial={"legal_representative_name": authorization.legal_representative_name}
    )
    return _render_legal_representative_authorization_form(request, authorization, form)


@require_POST
def update_legal_representative_authorization(request, token):
    authorization = _find(token)
    if not authorization or _is_signed(authorization):
        return redirect("show_legal_representative_authorization", token=token)
    form = LegalRepresentativeAuthorizationForm(data=request.POST)
    if not form.is_valid():
        return _render_legal_representative_authorization_form(request, authorization, form)
    result = SignLegalRepresentativeAuthorization(
        authorization=authorization,
        legal_representative_name=form.cleaned_data["legal_representative_name"],
        relationship=form.cleaned_data["relationship"],
        newsletter_consent=form.cleaned_data["newsletter_consent"],
        ip_address=client_ip(request),
    )
    for error in result.errors:
        messages.error(request, error)
    return redirect("show_legal_representative_authorization", token=token)


def _find(token):
    return (
        LegalRepresentativeAuthorization.objects.select_related("beneficiary")
        .filter(token=token)
        .first()
    )


def _is_signed(authorization):
    return authorization.status == LegalRepresentativeAuthorization.Status.SIGNED


def _render_legal_representative_authorization_form(request, authorization, form):
    return render(
        request,
        "legal_representative_authorization/edit_legal_representative_authorization.html",
        {"authorization": authorization, "beneficiary": authorization.beneficiary, "form": form},
    )
