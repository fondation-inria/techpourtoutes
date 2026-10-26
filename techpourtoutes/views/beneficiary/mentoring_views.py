from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from ...decorators import beneficiary_required
from ...forms import BeneficiaryMentoringSignUpForm, BeneficiaryStudyStatusForm
from ...services.beneficiary.upsert_beneficiary import UpsertBeneficiary
from ...utils.missing_record import report_missing_record
from ..beneficiary_views import (
    TRAINING_EXPERIENCE_FORMS,
    is_minor,
    relay_errors,
    require_legal_representative,
    training_experience_context,
)

# She already has an account, so this funnel is stateful: every answer is either read off her
# record or saved as it comes, and the hidden `action` says which step is coming back.


@beneficiary_required
def mentoring_funnel(request):
    beneficiary = request.user.beneficiary
    if beneficiary.is_registered_for_mentoring:
        messages.info(request, "Tu es déjà inscrite au programme de mentorat.")
        return redirect(reverse("show_account"))

    if request.method != "POST":
        return _start_mentoring(request, beneficiary)
    submit = _MENTORING_SUBMITS.get(request.POST.get("action"), _start_mentoring)
    return submit(request, beneficiary)


# An account imported from Faveod has no parcours, and Jobirl cannot register a mentoree without
# one: she answers the funnel's two questions before reaching the mentoring ones.
def _start_mentoring(request, beneficiary):
    if beneficiary.training_experiences.exists():
        return _mentoring_signup_step(request, beneficiary)
    return _render_mentoring_step(request, "study_status", form=BeneficiaryStudyStatusForm())


def _submit_study_status(request, beneficiary):
    form = BeneficiaryStudyStatusForm(data=request.POST)
    if not form.is_valid():
        return _render_mentoring_step(request, "study_status", form=form)
    return _training_experience_step(request, form.cleaned_data["study_status"])


def _submit_training_experience(request, beneficiary):
    study_status = request.POST.get("study_status")
    if study_status not in TRAINING_EXPERIENCE_FORMS:
        return _render_mentoring_step(request, "study_status", form=BeneficiaryStudyStatusForm())
    form = TRAINING_EXPERIENCE_FORMS[study_status](data=request.POST)
    if not form.is_valid():
        return _training_experience_step(request, study_status, form)
    if form.out_of_scope_postal_code:
        beneficiary.postal_code = form.out_of_scope_postal_code
        beneficiary.save()
    # Saved on its own: the parcours belongs to her account whether or not she finishes the last
    # step, and nothing then has to be carried over to it.
    form.save(beneficiary)
    report_missing_record(form, beneficiary, "Inscription mentorat")
    return _mentoring_signup_step(request, beneficiary)


def _submit_mentoring_signup(request, beneficiary):
    form = BeneficiaryMentoringSignUpForm(
        data=request.POST, asks_postal_code=_asks_postal_code(beneficiary)
    )
    require_legal_representative(form, is_minor(beneficiary.birth_date))
    if form.is_valid() and _sign_up_for_mentoring(request, beneficiary, form):
        return HttpResponse(headers={"HX-Redirect": reverse("show_account")})
    return _mentoring_signup_step(request, beneficiary, form)


_MENTORING_SUBMITS = {
    "study_status": _submit_study_status,
    "training_experience": _submit_training_experience,
    "mentoring_signup": _submit_mentoring_signup,
}


def _sign_up_for_mentoring(request, beneficiary, form):
    result = UpsertBeneficiary(beneficiary=beneficiary, mentoring_signup_data=form.cleaned_data)
    if result.failure:
        beneficiary.refresh_from_db()
        relay_errors(request, result)
        return False
    messages.success(
        request, "Ton inscription au programme de mentorat a bien été prise en compte."
    )
    return True


def _training_experience_step(request, study_status, form=None):
    return _render_mentoring_step(
        request,
        "training_experience",
        **training_experience_context(study_status, form),
    )


def _mentoring_signup_step(request, beneficiary, form=None):
    return _render_mentoring_step(
        request,
        "mentoring_signup",
        form=form or BeneficiaryMentoringSignUpForm(),
        is_minor=is_minor(beneficiary.birth_date),
        asks_postal_code=_asks_postal_code(beneficiary),
    )


def _asks_postal_code(beneficiary):
    return not beneficiary.postal_code and beneficiary.training_experiences.first().school is None


def _render_mentoring_step(request, step, **context):
    # The shell carries the first screen; every later step is swapped in on its own.
    step_template = f"beneficiary/funnels/partials/mentoring/steps/{step}.html"
    return render(
        request,
        "beneficiary/funnels/mentoring_funnel.html" if request.method == "GET" else step_template,
        {
            "step": step,
            "step_template": step_template,
            **context,
        },
    )
