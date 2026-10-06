from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ...decorators import beneficiary_required
from ...forms import BeneficiaryTrainingAmbassadorRequestForm
from ...services.beneficiary.upsert_beneficiary import UpsertBeneficiary
from ..beneficiary_views import relay_errors


@beneficiary_required
def new_training_ambassador_request(request):
    if request.user.beneficiary.has_requested_training_ambassador:
        return _redirect_already_requested(request)
    return _render_training_ambassador_request_form(
        request, BeneficiaryTrainingAmbassadorRequestForm()
    )


@require_POST
@beneficiary_required
def create_training_ambassador_request(request):
    beneficiary = request.user.beneficiary
    if beneficiary.has_requested_training_ambassador:
        return _redirect_already_requested(request)
    form = BeneficiaryTrainingAmbassadorRequestForm(data=request.POST)
    if not form.is_valid():
        return _render_training_ambassador_request_form(request, form)
    result = UpsertBeneficiary(
        beneficiary=beneficiary, training_ambassador_request_data=form.cleaned_data
    )
    if result.failure:
        relay_errors(request, result)
        return _render_training_ambassador_request_form(request, form)
    messages.success(request, "Ta demande a bien été envoyée, nous revenons vers toi très vite.")
    return redirect("show_account")


def _redirect_already_requested(request):
    messages.info(request, "Tu as déjà demandé à échanger avec une étudiante ambassadrice.")
    return redirect("show_account")


def _render_training_ambassador_request_form(request, form):
    return render(request, "beneficiary/new_training_ambassador_request.html", {"form": form})
