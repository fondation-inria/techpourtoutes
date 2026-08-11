from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from ..forms import BeneficiaryTrainingExperienceForm, ProTrainingExperienceForm
from ..models import TrainingExperience
from ..utils.training_experience import training_experience_insertion_anchor


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
    beneficiary, experience = _resolve_beneficiary_training_experience_target(request, pk)
    form = BeneficiaryTrainingExperienceForm(
        data=request.POST if request.method == "POST" else None,
        beneficiary=beneficiary,
        experience=experience,
        current_year=request.GET.get("current_year") == "true",
    )

    if request.method == "POST" and form.is_valid():
        return _submit_beneficiary_training_experience_form(request, form, beneficiary, experience)

    return render(
        request,
        "account/partials/beneficiary_training_experience_edit_form.html",
        {"form": form, "experience": experience},
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


# --------------------- private ----------------


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


def _resolve_beneficiary_training_experience_target(request, pk):
    if pk is None:
        return _get_beneficiary(request), None
    return None, _get_beneficiary_training_experience(request, pk)


def _submit_beneficiary_training_experience_form(request, form, beneficiary, experience):
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


def _reject_last_training_experience(request, experience):
    if _has_other_training_experience(experience):
        return None
    messages.error(request, "Au moins une formation doit être renseignée.")
    return HttpResponse(headers={"HX-Redirect": reverse("account")})


def _has_other_training_experience(experience):
    return experience.user.training_experiences.exclude(pk=experience.pk).exists()
