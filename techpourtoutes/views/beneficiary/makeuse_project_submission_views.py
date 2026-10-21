from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ...decorators import beneficiary_required
from ...forms import BeneficiaryMakeuseProjectSubmissionForm
from ...services.beneficiary.notify_makeuse_project_submission import (
    NotifyMakeuseProjectSubmission,
)


@beneficiary_required
def new_makeuse_project_submission(request):
    return _render_makeuse_project_submission_form(
        request, BeneficiaryMakeuseProjectSubmissionForm()
    )


@require_POST
@beneficiary_required
def create_makeuse_project_submission(request):
    form = BeneficiaryMakeuseProjectSubmissionForm(data=request.POST)
    if not form.is_valid():
        return _render_makeuse_project_submission_form(request, form)
    NotifyMakeuseProjectSubmission(beneficiary=request.user.beneficiary, **form.cleaned_data)
    messages.success(
        request,
        "La présentation de ton projet a bien été transmise à notre équipe, "
        "nous revenons vers toi très vite.",
    )
    return redirect("show_account")


def _render_makeuse_project_submission_form(request, form):
    return render(request, "beneficiary/new_makeuse_project_submission.html", {"form": form})
