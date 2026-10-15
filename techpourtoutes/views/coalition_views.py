from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..forms import ManifesteSignatureForm
from ..tasks import upsert_manifeste_signatory_task

MANIFESTE_TEMPLATE = "coalition/new_manifeste_signature.html"


def coalition_home(request):
    return render(request, "coalition/coalition_home.html", {})


def new_mentor(request):
    return render(request, "coalition/new_mentor.html", {})


def new_work_ambassador(request):
    return render(request, "coalition/new_work_ambassador.html", {})


def new_training_ambassador(request):
    return render(request, "coalition/new_training_ambassador.html", {})


def new_structure_engagement(request):
    return render(request, "coalition/new_structure_engagement.html", {})


def new_internship(request):
    return render(request, "coalition/new_internship.html", {})


def new_workshop_request(request):
    return render(request, "coalition/new_workshop_request.html", {})


def new_manifeste_signature(request):
    return render(request, MANIFESTE_TEMPLATE, {"form": ManifesteSignatureForm()})


@require_POST
def create_manifeste_signature(request):
    form = ManifesteSignatureForm(data=request.POST)
    if not form.is_valid():
        messages.error(
            request,
            "Des erreurs empêchent la validation du formulaire, "
            "merci de les corriger et de réessayer à nouveau.",
        )
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
