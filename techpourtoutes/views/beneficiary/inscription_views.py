from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from ...forms import (
    BeneficiaryEmailForm,
    BeneficiaryIdentityForm,
    BeneficiaryMentoringSignUpForm,
    BeneficiaryStudyStatusForm,
    BeneficiaryTrainingAmbassadorRequestForm,
    VerificationCodeForm,
)
from ...mailers import AuthMailer
from ...models import User
from ...ratelimit import rate_limit
from ...services.beneficiary.upsert_beneficiary import UpsertBeneficiary
from ...utils.dates import compute_age
from ...utils.funnel import FunnelSession, FunnelSteps
from ..beneficiary_views import (
    TRAINING_EXPERIENCE_FORMS,
    is_minor,
    relay_errors,
    require_legal_representative,
    save_pending_event,
    training_experience_context,
)


# Every way in from elsewhere on the site starts over, while the URL it redirects to resumes:
# reloading it keeps her answers.
def new_inscription_funnel(request):
    if request.user.is_authenticated:
        return redirect(reverse("show_account"))
    funnel = _funnel(request)
    funnel.clear()
    funnel.update(
        wants_mentor=request.GET.get("wants_mentor") == "1",
        wants_training_ambassador=request.GET.get("wants_training_ambassador") == "1",
        saved_event=request.GET.get("saved_event", ""),
    )
    return redirect(reverse("inscription_funnel"))


def inscription_funnel(request):
    if request.user.is_authenticated:
        return redirect(reverse("show_account"))

    # The answers given so far live in the session, so every POST only carries its own screen.
    if request.method != "POST":
        return _resume(request)

    handlers = {
        "back": _handle_back,
        "skip": _handle_skip,
        "code": _handle_code,
        "resend": _handle_resend,
    }
    handler = handlers.get(request.POST.get("action"), _advance)
    return handler(request)


def show_skip_inscription_step_modal(request, step):
    if step not in _FUNNEL.optional:
        raise Http404
    return render(
        request,
        "beneficiary/funnels/partials/inscription/show_skip_inscription_step_modal.html",
        {"step": step},
    )


# ------------------- actions -------------------


def _funnel(request):
    return FunnelSession(request, "inscription_funnel")


def _resume(request):
    step = _funnel(request).current_step or _FUNNEL.first
    return render(
        request,
        "beneficiary/funnels/inscription_funnel.html",
        {**_step_context(request, step), "messages_in_layout": True},
    )


def _advance(request):
    # Each step validates its own answers and is saved only once valid.
    step = request.POST.get("action")
    if step not in _STEP_VALIDATORS:
        step = _FUNNEL.first
    try:
        _require_earlier_steps(request, step)
        _STEP_VALIDATORS[step](request, _funnel(request).answers_with(step, request.POST))
    except _StepInterrupt as interrupt:
        return interrupt.response
    _funnel(request).save_step(step, request.POST)
    return _continue_after(request, step)


def _handle_back(request):
    funnel = _funnel(request)
    if funnel.current_step is None:
        return _render_lost_progress(request, _FUNNEL.first)
    return _render_step(request, _FUNNEL.previous(funnel.current_step, funnel.answers))


def _handle_skip(request):
    step = request.POST.get("step")
    if step not in _FUNNEL.optional:
        return _render_step(request, _FUNNEL.first)
    try:
        _require_earlier_steps(request, step)
    except _StepInterrupt as interrupt:
        return interrupt.response
    _funnel(request).update(**{_FUNNEL.optional[step]: False})
    return _continue_after(request, step)


# Once the last screen is answered, the account is created.
def _continue_after(request, step):
    following = _FUNNEL.next(step, _funnel(request).answers)
    if following is None:
        return _create_beneficiary(request)
    return _render_step(request, following)


def _create_beneficiary(request):
    answers = _funnel(request).answers
    try:
        validated = {
            step: _STEP_VALIDATORS[step](request, answers) for step in _FUNNEL.active(answers)
        }
    except _StepInterrupt as interrupt:
        return interrupt.response

    result = UpsertBeneficiary(
        beneficiary_data=validated["email"] | validated["identity"],
        training_experience_form=validated["training_experience"],
        mentoring_signup_data=validated.get("mentoring_signup"),
        training_ambassador_request_data=validated.get("training_ambassador_request"),
    )
    if result.failure:
        relay_errors(request, result)
        return _render_step(request, _FUNNEL.last(answers))
    _funnel(request).clear()
    return _render_step(
        request, "code", email=result.beneficiary.email, saved_event=answers.get("saved_event", "")
    )


# ------------------- lost progress -------------------

_LOST_PROGRESS = (
    "Ton inscription a expiré ou a été recommencée dans un autre onglet. Reprends à partir d'ici."
)


# A screen only counts once every screen before it has been answered: the session may have
# expired, or been started over from another tab, since that screen was displayed.
def _require_earlier_steps(request, step):
    funnel = _funnel(request)
    missing = _FUNNEL.missing_before(step, funnel.answered, funnel.answers)
    if missing is not None:
        raise _StepInterrupt(_render_lost_progress(request, missing))


def _render_lost_progress(request, step):
    messages.error(request, _LOST_PROGRESS)
    return _render_step(request, step)


# ------------------- login code -------------------

_CODE_ERROR = "Code invalide ou expiré."
_RESEND_NOTICE = "Un nouveau code t'a été envoyé par mail."


def _handle_code(request):
    email = request.POST.get("email", "")
    user = User.objects.filter(email=email, is_active=True).first()
    form = VerificationCodeForm(request.POST)
    if form.is_valid() and user is not None and user.consume_login_code(form.cleaned_data["code"]):
        # required because django-axes is configured
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)
        request.session["show_welcome_modal"] = True
        saved_event = save_pending_event(request, request.POST.get("saved_event", ""))
        landing = "index_beneficiary_events" if saved_event else "show_account"
        return HttpResponse(headers={"HX-Redirect": reverse(landing)})
    messages.error(request, _CODE_ERROR)
    return _render_step(
        request, "code", email=email, saved_event=request.POST.get("saved_event", "")
    )


@rate_limit("RATELIMIT_LOGIN", keys=("email",))
def _handle_resend(request):
    email = request.POST.get("email", "")
    user = User.objects.filter(email=email, is_active=True).first()
    if user is not None:
        AuthMailer.login_code(user=user, code=user.issue_login_code())
    messages.success(request, _RESEND_NOTICE)
    return _render_step(
        request, "code", email=email, saved_event=request.POST.get("saved_event", "")
    )


# ------------------- validation -------------------


class _StepInterrupt(Exception):
    # Raised by a step validator to short-circuit with a ready-made response: a re-render with
    # errors, a login redirect for an existing email, or an age-gated terminal screen.
    def __init__(self, response):
        self.response = response


def _validate_email(request, answers):
    form = BeneficiaryEmailForm(data=answers)
    if not form.is_valid():
        raise _StepInterrupt(_render_step(request, "email", form=form))
    existing = _login_redirect_for_existing_email(request, form.cleaned_data["email"], answers)
    if existing is not None:
        raise _StepInterrupt(existing)
    return form.cleaned_data


def _validate_identity(request, answers):
    form = BeneficiaryIdentityForm(data=answers)
    if not form.is_valid():
        raise _StepInterrupt(_render_step(request, "identity", form=form))
    age = compute_age(birth_date=form.cleaned_data["birth_date"])
    if age < 15 or age > 25:
        raise _StepInterrupt(_render_age_dead_end(request, "too_young" if age < 15 else "too_old"))
    return form.cleaned_data


def _validate_study(request, answers):
    form = BeneficiaryStudyStatusForm(data=answers)
    if not form.is_valid():
        raise _StepInterrupt(_render_step(request, "study_status", form=form))
    return form.cleaned_data


def _validate_training_experience(request, answers):
    form = TRAINING_EXPERIENCE_FORMS[answers["study_status"]](data=answers)
    if not form.is_valid():
        raise _StepInterrupt(_render_step(request, "training_experience", form=form))
    return form


def _validate_mentoring_signup(request, answers):
    form = BeneficiaryMentoringSignUpForm(data=answers)
    require_legal_representative(form, is_minor(_birth_date(answers)))
    if not form.is_valid():
        raise _StepInterrupt(_render_step(request, "mentoring_signup", form=form))
    return form.cleaned_data


def _validate_training_ambassador_request(request, answers):
    form = BeneficiaryTrainingAmbassadorRequestForm(data=answers)
    if not form.is_valid():
        raise _StepInterrupt(_render_step(request, "training_ambassador_request", form=form))
    return form.cleaned_data


def _login_redirect_for_existing_email(request, email, answers):
    user = User.objects.filter(email=email).first()
    if user is None:
        return None
    messages.error(request, "Un compte existe déjà avec cet email.")
    back_url = reverse("coalition_home" if hasattr(user, "pro") else "home")
    next_url = reverse(_destination_view_for_existing_user(user, answers))
    params = {
        "back": back_url,
        "next": next_url,
        "saved_event": answers.get("saved_event", ""),
    }
    login_url = f"{reverse('login_request')}?{urlencode(params)}"
    _funnel(request).clear()
    return HttpResponse(headers={"HX-Redirect": login_url})


def _destination_view_for_existing_user(user, data):
    if hasattr(user, "pro"):
        return "coalition_home"
    if _wants_mentor(data) and hasattr(user, "beneficiary"):
        return (
            "show_account" if user.beneficiary.is_registered_for_mentoring else "mentoring_funnel"
        )
    if _wants_training_ambassador(data) and hasattr(user, "beneficiary"):
        return (
            "show_account"
            if user.beneficiary.has_requested_training_ambassador
            else "new_training_ambassador_request"
        )
    return "home"


_STEP_VALIDATORS = {
    "email": _validate_email,
    "identity": _validate_identity,
    "study_status": _validate_study,
    "training_experience": _validate_training_experience,
    "mentoring_signup": _validate_mentoring_signup,
    "training_ambassador_request": _validate_training_ambassador_request,
}


# ------------------- answers -------------------


def _wants_mentor(data):
    return data.get("wants_mentor", False)


def _wants_training_ambassador(data):
    return data.get("wants_training_ambassador", False)


def _birth_date(data):
    """The identity screen sends an ISO date; anything else settles nothing."""
    try:
        return date.fromisoformat(data.get("birth_date", ""))
    except ValueError:
        return None


_FUNNEL = FunnelSteps(
    (
        "email",
        "identity",
        "study_status",
        "training_experience",
        "mentoring_signup",
        "training_ambassador_request",
    ),
    optional={
        "mentoring_signup": "wants_mentor",
        "training_ambassador_request": "wants_training_ambassador",
    },
)


# ------------------- rendering -------------------

# The training experience screen is left out: its form depends on the study status.
_STEP_FORMS = {
    "email": BeneficiaryEmailForm,
    "identity": BeneficiaryIdentityForm,
    "study_status": BeneficiaryStudyStatusForm,
    "mentoring_signup": BeneficiaryMentoringSignUpForm,
    "training_ambassador_request": BeneficiaryTrainingAmbassadorRequestForm,
}


def _render_step(request, step, *, form=None, **extra):
    if step in _FUNNEL.steps:
        _funnel(request).current_step = step
    context = _step_context(request, step, form, **extra)
    return render(request, context["step_template"], context)


def _render_age_dead_end(request, template):
    _funnel(request).clear()
    return render(request, f"beneficiary/funnels/partials/inscription/{template}.html", {})


def _step_context(request, step, form=None, **extra):
    data = _funnel(request).answers
    context = {
        "step": step,
        "step_template": f"beneficiary/funnels/partials/inscription/{step}.html",
        "progress": _FUNNEL.progress(step, data),
        "first_name": data.get("first_name"),
        "is_minor": is_minor(_birth_date(data)),
        "wants_mentor": _wants_mentor(data),
        "wants_training_ambassador": _wants_training_ambassador(data),
        **extra,
    }
    if step in _STEP_FORMS:
        context["form"] = form or _STEP_FORMS[step](initial=data)
    if step == "training_experience":
        # `initial` is rewritten by the form, so it needs a mutable copy of the answers.
        context.update(training_experience_context(data.get("study_status"), form, initial=data))
    return context
