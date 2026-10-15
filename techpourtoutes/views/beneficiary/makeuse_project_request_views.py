from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ...decorators import beneficiary_required
from ...forms import BeneficiaryMakeuseProjectRequestForm
from ...services.beneficiary.request_makeuse_project import RequestMakeuseProject


@beneficiary_required
def new_makeuse_project_request(request):
    return _render_makeuse_project_request_form(request, BeneficiaryMakeuseProjectRequestForm())


@require_POST
@beneficiary_required
def create_makeuse_project_request(request):
    form = BeneficiaryMakeuseProjectRequestForm(data=request.POST)
    if not form.is_valid():
        return _render_makeuse_project_request_form(request, form)
    RequestMakeuseProject(beneficiary=request.user.beneficiary, **form.cleaned_data)
    messages.success(request, "Ta demande a bien été envoyée, nous revenons vers toi très vite.")
    return redirect("show_account")


def _render_makeuse_project_request_form(request, form):
    return render(request, "beneficiary/new_makeuse_project_request.html", {"form": form})
