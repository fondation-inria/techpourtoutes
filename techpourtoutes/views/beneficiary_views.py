from django.conf import settings
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
    EmailNotificationForm,
    StudyStatus,
    VerificationCodeForm,
)
from ..mailers import AuthMailer
from ..models import Beneficiary, User
from ..ratelimit import rate_limit
from ..tasks import send_beneficiary_welcome_email_task, upsert_email_notification_task
from ..utils.dates import compute_age
from ..utils.missing_record import report_missing_record

# Delay before the welcome email is sent, so it doesn't land before the login code.
_WELCOME_EMAIL_DELAY_SECONDS = 5 * 60

# The funnel steps in order — the single source of truth navigation is derived from.
_STEPS = ("email", "identity", "study_status", "training_experience")

# Progress bar percentage per step. We actually start the % at the identity step
# (hence no + 1 after index and len(_STEPS))
_STEP_PROGRESS = {step: round(100 * (index) / (len(_STEPS))) for index, step in enumerate(_STEPS)}

_TRAINING_EXPERIENCE_FORMS = {
    StudyStatus.HIGH_SCHOOL: BeneficiaryHighSchoolTrainingExperienceForm,
    StudyStatus.HIGHER_EDUCATION: BeneficiaryHigherEducationTrainingExperienceForm,
    StudyStatus.FINISHED: BeneficiaryLastDiplomaTrainingExperienceForm,
    StudyStatus.RESUMING: BeneficiaryLastDiplomaTrainingExperienceForm,
}


def beneficiary_home(request):
    return render(request, "beneficiary/beneficiary_home.html", {})


def bientot_disponible(request):
    if request.method == "POST":
        form = EmailNotificationForm(data=request.POST)
        if form.is_valid():
            if settings.BREVO_SYNC_ENABLED:
                upsert_email_notification_task.delay(email=form.cleaned_data["email"])
            messages.success(
                request,
                "Merci, nous te préviendrons dès que cette fonctionnalité sera disponible.",
            )
            return redirect("bientot_disponible")
        messages.error(
            request,
            "Des erreurs empêchent la validation du formulaire, "
            "merci de les corriger et de réessayer à nouveau.",
        )
    else:
        form = EmailNotificationForm()
    return render(request, "static/bientot_disponible.html", {"form": form})


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
        "back": _handle_back,
        "code": _handle_code,
        "resend": _handle_resend,
        # The one step that doesn't move forward: submitting the last one creates the account.
        _STEPS[-1]: _create_beneficiary,
    }
    handler = handlers.get(request.POST.get("action"), _advance)
    return handler(request)


# ------------------- actions -------------------


def _handle_resume(request):
    return _render_step(request, _resume_step(request.POST))


def _advance(request):
    # Each forward step validates its own answers, then hands off to the next screen.
    step = request.POST.get("action")
    if step not in _STEP_VALIDATORS:
        step = _STEPS[0]
    try:
        _STEP_VALIDATORS[step](request)
    except _StepInterrupt as interrupt:
        return interrupt.response
    return _render_step(request, _next_step(step))


def _handle_back(request):
    return _render_step(request, _previous_step(request.POST.get("to")))


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
    report_missing_record(training_experience_form, beneficiary, "Funnel d'inscription")
    AuthMailer.login_code(user=beneficiary, code=beneficiary.issue_login_code())
    send_beneficiary_welcome_email_task.apply_async(
        kwargs={"beneficiary_pk": str(beneficiary.pk)}, countdown=_WELCOME_EMAIL_DELAY_SECONDS
    )
    response = _render_step(request, "code", email=beneficiary.email)
    response["HX-Trigger"] = "funnelReset"
    return response


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


# ------------------- validation -------------------

_EMAIL_ERROR = "Ton adresse mail n'est pas valide, corrige-la pour continuer."
_IDENTITY_ERROR = (
    "Certaines informations sont incomplètes ou invalides, corrige-les pour continuer."
)
_STUDY_ERROR = "Indique où tu en es dans tes études pour continuer."


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
    age = compute_age(birth_date=form.cleaned_data["birth_date"])
    if age < 15 or age > 25:
        raise _StepInterrupt(_render_age_dead_end(request, "too_young" if age < 15 else "too_old"))
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


def _login_redirect_for_existing_email(request, email):
    user = User.objects.filter(email=email).first()
    if user is None:
        return None
    messages.error(request, "Un compte existe déjà avec cet email.")
    back_url = reverse("coalition_home" if hasattr(user, "pro") else "home")
    login_url = f"{reverse('login_request')}?{urlencode({'back': back_url})}"
    return HttpResponse(headers={"HX-Redirect": login_url, "HX-Trigger": "funnelReset"})


_STEP_VALIDATORS = {
    "email": _validate_email,
    "identity": _validate_identity,
    "study_status": _validate_study,
}


# ------------------- navigation -------------------

_STEP_FORMS = {
    "email": BeneficiaryEmailForm,
    "identity": BeneficiaryIdentityForm,
    "study_status": BeneficiaryStudyStatusForm,
}


def _next_step(step):
    return _STEPS[_STEPS.index(step) + 1]


def _previous_step(step):
    if step not in _STEPS:
        return _STEPS[0]
    return _STEPS[max(_STEPS.index(step) - 1, 0)]


def _resume_step(data):
    for step in _STEPS[:-1]:
        if not _has_answer_for(_STEP_FORMS[step], data):
            return step
    if data.get("study_status") not in _TRAINING_EXPERIENCE_FORMS:
        return "study_status"
    return _STEPS[-1]


def _has_answer_for(form_class, data):
    return any(field in data for field in form_class.base_fields)


# ------------------- rendering -------------------

_FORM_BUILDERS = {
    "email": lambda data: BeneficiaryEmailForm(initial={"email": data.get("email")}),
    "identity": lambda data: BeneficiaryIdentityForm(initial=data),
    "study_status": lambda data: BeneficiaryStudyStatusForm(
        initial={"study_status": data.get("study_status")}
    ),
}


def _render_step(request, step, *, form=None, **extra):
    context = _step_context(request, step, form, **extra)
    return render(request, f"beneficiary/partials/inscription/{step}.html", context)


def _render_step_with_error(request, step, error, **extra):
    if error:
        messages.error(request, error)
    return _render_step(request, step, **extra)


def _render_age_dead_end(request, template):
    response = render(request, f"beneficiary/partials/inscription/{template}.html", {})
    response["HX-Trigger"] = "funnelReset"
    return response


def _step_context(request, step, form=None, **extra):
    data = request.POST
    context = {
        "step": step,
        "progress": _STEP_PROGRESS.get(step),
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
