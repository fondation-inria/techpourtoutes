from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from ..forms import BeneficiaryTrainingExperienceForm, ProTrainingExperienceForm
from ..models import TrainingExperience
from ..utils.missing_record import report_missing_record
from ..utils.training_experience import training_experience_insertion_anchor


@login_required
def show_pro_training_experience(request, pk):
    experience = _get_pro_training_experience(request, pk)
    return render(
        request,
        "account/partials/show_pro_training_experience.html",
        {"experience": experience},
    )


@login_required
def edit_pro_training_experience(request, pk):
    experience = _get_pro_training_experience(request, pk)
    return _render_pro_training_experience_form(
        request, experience, ProTrainingExperienceForm(experience=experience)
    )


@require_POST
@login_required
def update_pro_training_experience(request, pk):
    experience = _get_pro_training_experience(request, pk)
    form = ProTrainingExperienceForm(data=request.POST)
    if not form.is_valid():
        return _render_pro_training_experience_form(request, experience, form)

    form.save(experience)
    report_missing_record(form, experience.user, "Compte pro")
    return render(
        request,
        "account/partials/show_pro_training_experience.html",
        {"experience": experience},
    )


@login_required
def new_beneficiary_training_experience(request):
    return _render_beneficiary_training_experience_form(
        request, beneficiary=_get_beneficiary(request), experience=None
    )


@require_POST
@login_required
def create_beneficiary_training_experience(request):
    return _submit_beneficiary_training_experience(
        request, beneficiary=_get_beneficiary(request), experience=None
    )


@login_required
def edit_beneficiary_training_experience(request, pk):
    return _render_beneficiary_training_experience_form(
        request, beneficiary=None, experience=_get_beneficiary_training_experience(request, pk)
    )


@require_POST
@login_required
def update_beneficiary_training_experience(request, pk):
    return _submit_beneficiary_training_experience(
        request, beneficiary=None, experience=_get_beneficiary_training_experience(request, pk)
    )


@login_required
def show_beneficiary_training_experience(request, pk):
    experience = _get_beneficiary_training_experience(request, pk)
    return _render_beneficiary_training_experience_item(request, experience)


@require_POST
@login_required
def destroy_beneficiary_training_experience(request, pk):
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
        "account/partials/show_beneficiary_training_experience.html",
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


def _beneficiary_training_experience_form(request, beneficiary, experience, data=None):
    return BeneficiaryTrainingExperienceForm(
        data=data,
        beneficiary=beneficiary,
        experience=experience,
        current_year=request.GET.get("current_year") == "true",
    )


def _render_pro_training_experience_form(request, experience, form):
    return render(
        request,
        "account/partials/edit_pro_training_experience.html",
        {"form": form, "experience": experience},
    )


def _render_beneficiary_training_experience_form(request, beneficiary, experience, form=None):
    return render(
        request,
        "account/partials/edit_beneficiary_training_experience.html",
        {
            "form": form
            or _beneficiary_training_experience_form(request, beneficiary, experience),
            "experience": experience,
        },
    )


def _submit_beneficiary_training_experience(request, beneficiary, experience):
    form = _beneficiary_training_experience_form(request, beneficiary, experience, request.POST)
    if not form.is_valid():
        return _render_beneficiary_training_experience_form(request, beneficiary, experience, form)
    return _save_beneficiary_training_experience(request, form, beneficiary, experience)


def _save_beneficiary_training_experience(request, form, beneficiary, experience):
    if form.cleaned_data.get("not_enrolled"):
        if experience is not None:
            rejection = _reject_last_training_experience(request, experience)
            if rejection:
                return rejection
            experience.delete()
        return _render_beneficiary_training_experience_item(request, experience=None)
    saved = form.save(experience or TrainingExperience(user=beneficiary))
    report_missing_record(form, saved.user, "Compte bénéficiaire")
    return _render_beneficiary_training_experience_item(
        request, saved, oob_swap=_training_experience_oob_swap(saved)
    )


def _reject_last_training_experience(request, experience):
    if _has_other_training_experience(experience):
        return None
    messages.error(request, "Au moins une formation doit être renseignée.")
    return HttpResponse(headers={"HX-Redirect": reverse("show_account")})


def _has_other_training_experience(experience):
    return experience.user.training_experiences.exclude(pk=experience.pk).exists()
