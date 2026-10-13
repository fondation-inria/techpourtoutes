from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from waffle.decorators import waffle_switch

from ...forms import (
    ProAdditionalInformationForm,
    ProEmailForm,
    ProEngagementsForm,
    ProIdentityForm,
    ProTrainingAmbassadorForm,
    ProWorkshopRequestForm,
    VerificationCodeForm,
)
from ...forms.pro_inscription import ENGAGEMENT_CHOICES, EVENTS
from ...mailers import AuthMailer
from ...models import Pro, User
from ...ratelimit import rate_limit
from ...services.pro.create_pro import CreatePro
from ...utils.funnel import FunnelSession, FunnelSteps

_SWITCH = "new_pro_features"


# Every way in from elsewhere on the site starts over, while the URL it redirects to resumes:
# reloading it keeps the answers.
@waffle_switch(_SWITCH)
def new_pro_inscription_funnel(request):
    if request.user.is_authenticated:
        return redirect(reverse("show_account"))
    funnel = _funnel(request)
    funnel.clear()
    funnel.update(preselected_engagement=_preselected_engagement(request.GET.get("engagement")))
    return redirect(reverse("pro_inscription_funnel"))


@waffle_switch(_SWITCH)
def pro_inscription_funnel(request):
    if request.user.is_authenticated:
        return redirect(reverse("show_account"))

    # The answers given so far live in the session, so every POST only carries its own screen.
    if request.method != "POST":
        return _resume(request)

    handlers = {
        "back": _handle_back,
        "code": _handle_code,
        "resend": _handle_resend,
    }
    handler = handlers.get(request.POST.get("action"), _advance)
    return handler(request)


# ------------------- actions -------------------


def _funnel(request):
    return FunnelSession(
        request, "pro_inscription_funnel", multiple=("engagements", "workshop-ateliers")
    )


def _resume(request):
    step = _funnel(request).current_step or _FUNNEL.first
    return render(
        request,
        "coalition/funnels/pro_inscription_funnel.html",
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


# Once the last screen is answered, the account is created.
def _continue_after(request, step):
    following = _FUNNEL.next(step, _funnel(request).answers)
    if following is None:
        return _create_pro(request)
    return _render_step(request, following)


def _create_pro(request):
    answers = _funnel(request).answers
    try:
        validated = {
            step: _STEP_VALIDATORS[step](request, answers) for step in _FUNNEL.active(answers)
        }
    except _StepInterrupt as interrupt:
        return interrupt.response

    result = CreatePro(
        identity=validated["email"] | validated["identity"],
        engagements=validated["engagements"],
        training_ambassador_form=validated.get("training_ambassador"),
        workshop_request_form=validated.get("workshop_request"),
        additional_information=validated.get("additional_information"),
    )
    if result.failure:
        for error in result.errors:
            messages.error(request, error)
        return _render_step(request, _FUNNEL.last(answers))
    _funnel(request).clear()
    return _render_step(
        request,
        "code",
        email=result.pro.email,
        events_only=answers["engagements"] == [EVENTS],
    )


# ------------------- lost progress -------------------

_LOST_PROGRESS = (
    "Votre inscription a expiré ou a été recommencée dans un autre onglet. "
    "Reprenez à partir d'ici."
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
_RESEND_NOTICE = "Un nouveau code vous a été envoyé par mail."


def _handle_code(request):
    email = request.POST.get("email", "")
    events_only = request.POST.get("events_only") == "1"
    user = User.objects.filter(email=email, is_active=True).first()
    form = VerificationCodeForm(request.POST)
    if form.is_valid() and user is not None and user.consume_login_code(form.cleaned_data["code"]):
        # required because django-axes is configured
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)
        request.session["show_welcome_modal"] = True
        landing = "index_pro_events" if events_only else "show_account"
        return HttpResponse(headers={"HX-Redirect": reverse(landing)})
    messages.error(request, _CODE_ERROR)
    return _render_step(request, "code", email=email, events_only=events_only)


@rate_limit("RATELIMIT_LOGIN", keys=("email",))
def _handle_resend(request):
    email = request.POST.get("email", "")
    user = User.objects.filter(email=email, is_active=True).first()
    if user is not None:
        AuthMailer.login_code(user=user, code=user.issue_login_code())
    messages.success(request, _RESEND_NOTICE)
    return _render_step(
        request, "code", email=email, events_only=request.POST.get("events_only") == "1"
    )


# ------------------- validation -------------------


class _StepInterrupt(Exception):
    # Raised by a step validator to short-circuit with a ready-made response: a re-render with
    # errors, or a login redirect for an existing email.
    def __init__(self, response):
        self.response = response


def _validate_email(request, answers):
    form = ProEmailForm(data=answers)
    if not form.is_valid():
        raise _StepInterrupt(_render_step(request, "email", form=form))
    if User.objects.filter(email=form.cleaned_data["email"]).exists():
        raise _StepInterrupt(_login_redirect_for_existing_email(request))
    return form.cleaned_data


def _validated(step):
    """A validator binding the screen's form to the answers, re-rendering it while invalid."""

    def validate(request, answers):
        form = _STEP_FORMS[step](data=answers, **_form_kwargs(step, answers))
        if not form.is_valid():
            raise _StepInterrupt(_render_step(request, step, form=form))
        return form

    return validate


def _cleaned(step):
    validate = _validated(step)
    return lambda request, answers: validate(request, answers).cleaned_data


def _login_redirect_for_existing_email(request):
    messages.error(request, "Un compte existe déjà avec cette adresse mail.")
    params = {"back": reverse("coalition_home"), "next": reverse("show_account")}
    _funnel(request).clear()
    return HttpResponse(headers={"HX-Redirect": f"{reverse('login_request')}?{urlencode(params)}"})


_STEP_FORMS = {
    "email": ProEmailForm,
    "identity": ProIdentityForm,
    "engagements": ProEngagementsForm,
    "training_ambassador": ProTrainingAmbassadorForm,
    "workshop_request": ProWorkshopRequestForm,
    "additional_information": ProAdditionalInformationForm,
}

# The training ambassador and workshop screens hand over their form: it saves what they ask.
_STEP_VALIDATORS = {
    "email": _validate_email,
    "identity": _cleaned("identity"),
    "engagements": _cleaned("engagements"),
    "training_ambassador": _validated("training_ambassador"),
    "workshop_request": _validated("workshop_request"),
    "additional_information": _cleaned("additional_information"),
}


# ------------------- answers -------------------


def _engagements(answers):
    return answers.get("engagements", [])


def _preselected_engagement(engagement):
    return engagement if engagement in dict(ENGAGEMENT_CHOICES) else ""


def _asks_additional_information(answers):
    others = (
        set(_engagements(answers))
        - set(Pro.Engagement.TRAINING_AMBASSADOR, Pro.Engagement.WORKSHOPS)
        - {EVENTS}
    )
    return bool(others) or _engagements(answers) == [EVENTS]


_FUNNEL = FunnelSteps(
    (
        "email",
        "identity",
        "engagements",
        "training_ambassador",
        "workshop_request",
        "additional_information",
    ),
    optional={
        "training_ambassador": lambda answers: (
            Pro.Engagement.TRAINING_AMBASSADOR in _engagements(answers)
        ),
        "workshop_request": lambda answers: Pro.Engagement.WORKSHOPS in _engagements(answers),
        "additional_information": _asks_additional_information,
    },
)


# ------------------- rendering -------------------


def _render_step(request, step, *, form=None, **extra):
    if step in _FUNNEL.steps:
        _funnel(request).current_step = step
    context = _step_context(request, step, form, **extra)
    return render(request, context["step_template"], context)


def _step_context(request, step, form=None, **extra):
    data = _funnel(request).answers
    context = {
        "step": step,
        "step_template": f"coalition/funnels/partials/pro_inscription/steps/{step}.html",
        "progress": _FUNNEL.progress(step, data),
        "funnel_url": reverse("pro_inscription_funnel"),
        "submit_label": _submit_label(step, data),
        **extra,
    }
    if step in _STEP_FORMS:
        context["form"] = form or _STEP_FORMS[step](
            initial=_initial(step, data), **_form_kwargs(step, data)
        )
    return context


def _submit_label(step, data):
    if step in _FUNNEL.steps and step == _FUNNEL.last(data):
        return "Rejoindre la coalition"
    return "Continuer"


def _form_kwargs(step, answers):
    if step == "additional_information" and "workshop_request" in _FUNNEL.active(answers):
        return {"workshop": _workshop_answers(answers)}
    return {}


def _initial(step, data):
    if step == "engagements" and data.get("preselected_engagement"):
        return {"engagements": [data["preselected_engagement"]], **data}
    if step == "workshop_request":
        return _workshop_answers(data)
    return data


def _workshop_answers(data):
    prefix = f"{ProWorkshopRequestForm.prefix}-"
    return {
        name.removeprefix(prefix): value for name, value in data.items() if name.startswith(prefix)
    }
