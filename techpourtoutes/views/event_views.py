from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..decorators import beneficiary_required, pro_required
from ..forms import EventDetailsForm, EventLocationForm, EventSubcategoryForm
from ..models import Event
from ..services.event.create_event import CreateEvent
from ..services.event.update_event import UpdateEvent

# The funnel steps in order — the single source of truth navigation is derived from.
_STEPS = ("subcategory", "details", "location")

_STEP_FORMS = {
    "subcategory": EventSubcategoryForm,
    "details": EventDetailsForm,
    "location": EventLocationForm,
}

# Never carried forward: they steer the funnel, they are not answers.
_CONTROL_FIELDS = {"action", "to", "csrfmiddlewaretoken", "q", "confirmed"}


@beneficiary_required
def index_beneficiary_events(request):
    events = request.user.beneficiary.saved_events
    return render(
        request,
        "beneficiary/index_beneficiary_events.html",
        {
            "upcoming_events": events.approved().upcoming(),
            "past_events": events.approved().past().order_by("-start_date", "-start_time"),
        },
    )


@pro_required
def index_pro_events(request):
    events = request.user.pro.events
    return render(
        request,
        "coalition/index_pro_events.html",
        {
            "upcoming_events": events.approved().upcoming(),
            "pending_events": events.pending(),
            "past_events": events.approved().past().order_by("-start_date", "-start_time"),
        },
    )


@pro_required
def new_event(request):
    """Renders `event_funnel.html` ;
    nothing is persisted until the last screen: the answers travel as hidden inputs."""
    return _render(request, "coalition/funnels/event_funnel.html", _STEPS[0], {})


@pro_required
def edit_event(request, pk):
    """Renders `event_funnel.html`, opened on the answers the event already holds ;
    nothing is persisted until the last screen: the answers travel as hidden inputs."""
    event = get_object_or_404(request.user.pro.events, pk=pk)
    answers = _answers_from(event)
    back = _safe_back(request, request.GET.get("back", ""))
    if back:
        answers["back"] = back
    return _render(
        request,
        "coalition/funnels/event_funnel.html",
        _STEPS[0],
        answers,
        quit_url=_show_event_url(event, back),
    )


@require_POST
@pro_required
def create_event(request):
    """Every screen of the creation funnel posts here: it moves one step on, one step back,
    or writes the event."""
    handlers = {"back": _handle_back, _STEPS[-1]: _create}
    return handlers.get(request.POST.get("action"), _advance)(request)


@require_POST
@pro_required
def update_event(request):
    """Every screen of the edit funnel posts here: it moves one step on, one step back,
    or writes the event."""
    handlers = {"back": _handle_back, _STEPS[-1]: _update}
    return handlers.get(request.POST.get("action"), _advance)(request)


# ------------------- private -------------------


class _StepInterrupt(Exception):
    """Raised by a step validator to short-circuit with a ready-made response."""

    def __init__(self, response):
        self.response = response


def _advance(request):
    step = request.POST.get("action")
    if step not in _STEP_FORMS:
        step = _STEPS[0]
    try:
        _validate(request, step)
    except _StepInterrupt as interrupt:
        return interrupt.response
    return _render_step(request, _next_step(step))


def _handle_back(request):
    return _render_step(request, _previous_step(request.POST.get("to")))


def _create(request):
    """The new funnel's last screen: the user is told its event now awaits validation — or,
    if he has publishing rights, that it is already online."""
    try:
        forms = _validated_answers(request)
    except _StepInterrupt as interrupt:
        return interrupt.response

    result = CreateEvent(pro=request.user.pro, forms=forms)
    return render(
        request, "coalition/funnels/partials/event/submitted.html", {"event": result.event}
    )


def _update(request):
    """The edit funnel's last screen: the user lands back on the event, updated."""
    try:
        forms = _validated_answers(request)
    except _StepInterrupt as interrupt:
        return interrupt.response

    event = _event_being_edited(request)
    if _needs_confirmation(event, request):
        return _render_step(request, _STEPS[-1], form=forms[-1], confirming=True)

    UpdateEvent(event=event, forms=forms)
    messages.success(request, "Votre événement a bien été modifié.")
    back = _safe_back(request, request.POST.get("back", ""))
    return HttpResponse(headers={"HX-Redirect": _show_event_url(event, back)})


def _show_event_url(event, back):
    url = reverse("show_event", args=[event.slug])
    return f"{url}?{urlencode({'back': back or reverse('index_pro_events')})}"


def _safe_back(request, candidate):
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    return ""


def _validated_answers(request):
    """The client can't be trusted, so the whole payload is replayed through every step's form.
    On the first failure she is sent back to that screen."""
    return tuple(_validate(request, step) for step in _STEPS)


def _event_being_edited(request):
    try:
        return request.user.pro.events.get(pk=request.POST.get("event", ""))
    except Event.DoesNotExist, ValidationError:
        raise Http404


def _needs_confirmation(event, request):
    """A published event has an audience: she is warned her changes will be mailed out to it.
    One still awaiting validation was never seen by anyone, so it is saved straight away."""
    return event.status == Event.Status.APPROVED and not request.POST.get("confirmed")


def _validate(request, step):
    form = _STEP_FORMS[step](data=request.POST)
    if not form.is_valid():
        raise _StepInterrupt(_render_step(request, step, form=form))
    return form


def _answers_from(event):
    answers = {"event": str(event.pk)}
    for form_class in _STEP_FORMS.values():
        answers |= form_class(event=event).initial
    return answers


def _render_step(request, step, *, form=None, confirming=False):
    partial = f"coalition/funnels/partials/event/{step}.html"
    return _render(request, partial, step, request.POST, form=form, confirming=confirming)


def _render(request, template, step, answers, *, form=None, confirming=False, quit_url=""):
    editing = bool(answers.get("event"))
    return render(
        request,
        template,
        {
            "step": step,
            "form": form or _STEP_FORMS[step](initial=dict(answers.items())),
            "carried": _carried(answers, step),
            "previous_step": _previous_step(step),
            "confirming": confirming,
            "editing": editing,
            "funnel_url": reverse("update_event" if editing else "create_event"),
            "quit_url": quit_url or reverse("show_account"),
        },
    )


def _carried(answers, step):
    """What the earlier screens collected, minus this one's own fields: they come back as
    visible inputs, and a duplicated name would let the stale hidden value win."""
    own = set(_STEP_FORMS[step].base_fields)
    return {
        name: value
        for name, value in answers.items()
        if name not in _CONTROL_FIELDS and name not in own
    }


def _next_step(step):
    return _STEPS[_STEPS.index(step) + 1]


def _previous_step(step):
    if step not in _STEPS:
        return _STEPS[0]
    return _STEPS[max(_STEPS.index(step) - 1, 0)]
