from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from ..forms import (
    BeneficiaryEmailForm,
    BeneficiaryHigherEducationTrainingExperienceForm,
    BeneficiaryHighSchoolTrainingExperienceForm,
    BeneficiaryIdentityForm,
    BeneficiaryLastDiplomaTrainingExperienceForm,
    BeneficiaryStudyStatusForm,
    StudyStatus,
    VerificationCodeForm,
)
from ..mailers import AuthMailer
from ..models import Beneficiary, User
from ..ratelimit import rate_limit
from ..tasks import send_beneficiary_welcome_email_task

# Delay before the welcome email is sent, so it doesn't land before the login code.
_WELCOME_EMAIL_DELAY_SECONDS = 5 * 60

# The funnel steps in order — the single source of truth navigation is derived from.
_STEPS = ("email", "identity", "study_status", "training_experience")

# Progress bar percentage per step. The "+ 1" reserves a final segment for the success screen,
# which shows no bar, so the last form step stops short of 100%.
STEP_PROGRESS = {
    step: round(100 * (index + 1) / (len(_STEPS) + 1)) for index, step in enumerate(_STEPS)
}

_TRAINING_EXPERIENCE_FORMS = {
    StudyStatus.HIGH_SCHOOL: BeneficiaryHighSchoolTrainingExperienceForm,
    StudyStatus.HIGHER_EDUCATION: BeneficiaryHigherEducationTrainingExperienceForm,
    StudyStatus.FINISHED: BeneficiaryLastDiplomaTrainingExperienceForm,
    StudyStatus.RESUMING: BeneficiaryLastDiplomaTrainingExperienceForm,
}


def beneficiary_home(request):
    return render(request, "beneficiary/beneficiary_home.html", {})


def inscription_funnel(request):
    if request.user.is_authenticated:
        return redirect(reverse("account"))

    # The funnel is stateless server-side: the accumulated answers live in the browser's
    # sessionStorage (Alpine) and travel with every POST. GET only renders the shell, which
    # asks the server for the right step through a "resume" POST once Alpine has hydrated.
    if request.method != "POST":
        return render(request, "beneficiary/inscription_funnel.html", {})

    handlers = {
        "resume": _handle_resume,
        "email": _advance,
        "identity": _advance,
        "study_status": _advance,
        "training_experience": _create_beneficiary,
        "code": _handle_code,
        "resend": _handle_resend,
        "back": _handle_back,
    }
    handler = handlers.get(request.POST.get("step"), _advance)
    return handler(request)


# ------------------- step handlers -------------------


def _handle_resume(request):
    return _render_step(request, _resume_step(request.POST))


def _advance(request):
    # Each forward step validates its own answers, then hands off to the next screen.
    step = request.POST.get("step")
    if step not in _STEP_VALIDATORS:
        step = "email"
    try:
        _STEP_VALIDATORS[step](request)
    except _StepInterrupt as interrupt:
        return interrupt.response
    return _render_step(request, _next_step(step))


def _create_beneficiary(request):
    # The client can't be trusted, so the whole payload is re-validated here, reusing each step's
    # validator. On the first failure the user is sent back to that screen with an error banner.
    try:
        email = _validate_email(request, error=_EMAIL_ERROR)
        identity = _validate_identity(request, error=_IDENTITY_ERROR)
        _validate_study(request, error=_STUDY_ERROR)
        training_experience_form = _validate_training_experience(request)
    except _StepInterrupt as interrupt:
        return interrupt.response

    beneficiary = Beneficiary(
        username=email["email"],
        email=email["email"],
        first_name=identity["first_name"],
        last_name=identity["last_name"],
        birth_date=identity["birth_date"],
        brevo_sync_enabled=identity["newsletter_consent"],
    )
    beneficiary.save()
    training_experience_form.save(beneficiary)
    AuthMailer.login_code(user=beneficiary, code=beneficiary.issue_login_code())
    send_beneficiary_welcome_email_task.apply_async(
        kwargs={"beneficiary_pk": str(beneficiary.pk)}, countdown=_WELCOME_EMAIL_DELAY_SECONDS
    )
    response = _render_step(request, "code", email=beneficiary.email)
    response["HX-Trigger"] = "funnelReset"
    return response


def _handle_code(request):
    # Terminal step: the code was mailed when the beneficiary was created. A valid code logs her
    # in and sends her to her account; an invalid one re-renders the screen with an error banner.
    email = request.POST.get("email", "")
    user = User.objects.filter(email=email, is_active=True).first()
    form = VerificationCodeForm(request.POST)
    if form.is_valid() and user is not None and user.consume_login_code(form.cleaned_data["code"]):
        # required because django-axes is configured
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)
        return HttpResponse(headers={"HX-Redirect": reverse("account")})
    return _render_step_with_error(request, "code", _CODE_ERROR, email=email)


@rate_limit("RATELIMIT_LOGIN", keys=("email",))
def _handle_resend(request):
    email = request.POST.get("email", "")
    user = User.objects.filter(email=email, is_active=True).first()
    if user is not None:
        AuthMailer.login_code(user=user, code=user.issue_login_code())
    messages.success(request, _RESEND_NOTICE)
    return _render_step(request, "code", email=email)


def _handle_back(request):
    return _render_step(request, _previous_step(request.POST.get("to")))


# ------------------- validation -------------------


class _StepInterrupt(Exception):
    # Raised by a step validator to short-circuit with a ready-made response: a re-render with
    # errors, a login redirect for an existing email, or an age-gated terminal screen.
    def __init__(self, response):
        self.response = response


def _validate_email(request, *, error=None):
    form = BeneficiaryEmailForm(data=request.POST)
    if not form.is_valid():
        raise _StepInterrupt(_render_step_with_error(request, "email", error, form=form))
    existing = _login_redirect_for_existing_email(request, form.cleaned_data["email"])
    if existing is not None:
        raise _StepInterrupt(existing)
    return form.cleaned_data


def _validate_identity(request, *, error=None):
    form = BeneficiaryIdentityForm(data=request.POST)
    if not form.is_valid():
        raise _StepInterrupt(_render_step_with_error(request, "identity", error, form=form))
    age = _age(form.cleaned_data["birth_date"])
    if age < 15 or age > 25:
        raise _StepInterrupt(_render_terminal(request, "too_young" if age < 15 else "too_old"))
    return form.cleaned_data


def _validate_study(request, *, error=None):
    form = BeneficiaryStudyStatusForm(data=request.POST)
    if not form.is_valid():
        raise _StepInterrupt(_render_step_with_error(request, "study_status", error, form=form))
    return form.cleaned_data


def _validate_training_experience(request):
    form = _TRAINING_EXPERIENCE_FORMS[request.POST["study_status"]](data=request.POST)
    if not form.is_valid():
        raise _StepInterrupt(_render_step(request, "training_experience", form=form))
    return form


_STEP_VALIDATORS = {
    "email": _validate_email,
    "identity": _validate_identity,
    "study_status": _validate_study,
}


# ------------------- private -------------------

_EMAIL_ERROR = "Ton adresse mail n'est pas valide, corrige-la pour continuer."
_IDENTITY_ERROR = (
    "Certaines informations sont incomplètes ou invalides, corrige-les pour continuer."
)
_STUDY_ERROR = "Indique où tu en es dans tes études pour continuer."
_CODE_ERROR = "Code invalide ou expiré."
_RESEND_NOTICE = "Un nouveau code t'a été envoyé par mail."


def _login_redirect_for_existing_email(request, email):
    user = User.objects.filter(email=email).first()
    if user is None:
        return None
    messages.error(request, "Un compte existe déjà avec cet email.")
    back_url = reverse("coalition_home" if hasattr(user, "pro") else "home")
    login_url = f"{reverse('login_request')}?{urlencode({'back': back_url})}"
    return HttpResponse(headers={"HX-Redirect": login_url, "HX-Trigger": "funnelReset"})


def _age(birth_date):
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def _next_step(step):
    return _STEPS[_STEPS.index(step) + 1]


def _previous_step(step):
    if step not in _STEPS:
        return _STEPS[0]
    return _STEPS[max(_STEPS.index(step) - 1, 0)]


_STEP_FORMS = {
    "email": BeneficiaryEmailForm,
    "identity": BeneficiaryIdentityForm,
    "study_status": BeneficiaryStudyStatusForm,
}


# Furthest step the client can resume to, based on which answers it already carries.
def _resume_step(data):
    for step in _STEPS[:-1]:
        if not _has_answer_for(_STEP_FORMS[step], data):
            return step
    # The last screen is picked from the study status, so an unknown one resumes on that question.
    if data.get("study_status") not in _TRAINING_EXPERIENCE_FORMS:
        return "study_status"
    return _STEPS[-1]


def _has_answer_for(form_class, data):
    return any(field in data for field in form_class.base_fields)


def _render_step(request, step, *, form=None, **extra):
    context = _step_context(request, step, form, **extra)
    return render(request, f"beneficiary/partials/inscription/{step}.html", context)


def _render_step_with_error(request, step, error, **extra):
    if error:
        messages.error(request, error)
    return _render_step(request, step, **extra)


def _render_terminal(request, template):
    # Age-gated dead-ends: tell the client to wipe its stored answers on the way out.
    response = render(request, f"beneficiary/partials/inscription/{template}.html", {})
    response["HX-Trigger"] = "funnelReset"
    return response


def _step_context(request, step, form=None, **extra):
    data = request.POST
    context = {
        "step": step,
        "progress": STEP_PROGRESS.get(step),
        "first_name": data.get("first_name"),
        **extra,
    }
    if step in _FORM_BUILDERS:
        context["form"] = form or _FORM_BUILDERS[step](data)
    if step == "training_experience":
        context.update(_training_experience_context(data, form))
    return context


def _training_experience_context(data, form):
    study_status = data.get("study_status")
    form_class = _TRAINING_EXPERIENCE_FORMS[study_status]
    # `initial` is rewritten by the form, so it needs a mutable copy of the answers.
    return {"study_status": study_status, "form": form or form_class(initial=data.dict())}


_FORM_BUILDERS = {
    "email": lambda data: BeneficiaryEmailForm(initial={"email": data.get("email")}),
    "identity": lambda data: BeneficiaryIdentityForm(initial=data),
    "study_status": lambda data: BeneficiaryStudyStatusForm(
        initial={"study_status": data.get("study_status")}
    ),
}
