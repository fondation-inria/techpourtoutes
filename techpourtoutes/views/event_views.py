from django.shortcuts import render

from ..decorators import pro_required
from ..forms import EventDetailsForm, EventLocationForm, EventSubcategoryForm
from ..services.event.create_event import CreateEvent

# The funnel steps in order — the single source of truth navigation is derived from.
_STEPS = ("subcategory", "details", "location")

_STEP_FORMS = {
    "subcategory": EventSubcategoryForm,
    "details": EventDetailsForm,
    "location": EventLocationForm,
}

# Never carried forward: they steer the funnel, they are not answers.
_CONTROL_FIELDS = {"action", "to", "csrfmiddlewaretoken", "q"}


@pro_required
def event_funnel(request):
    """Nothing is persisted until the last screen: the answers travel as hidden inputs, so
    closing the tab loses them — hence the confirmation modal on the way out.
    """
    if request.method != "POST":
        return _render_step(request, _STEPS[0])
    handlers = {"back": _handle_back, _STEPS[-1]: _create_event}
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


def _create_event(request):
    # The client can't be trusted, so the whole payload is re-validated here, reusing each
    # step's form. On the first failure the user is sent back to that screen.
    try:
        forms = tuple(_validate(request, step) for step in _STEPS)
    except _StepInterrupt as interrupt:
        return interrupt.response

    CreateEvent(pro=request.user.pro, forms=forms)
    return render(request, "coalition/partials/event/submitted.html", {})


def _validate(request, step):
    form = _STEP_FORMS[step](data=request.POST)
    if not form.is_valid():
        raise _StepInterrupt(_render_step(request, step, form=form))
    return form


def _render_step(request, step, *, form=None):
    # The shell carries the first screen; every later step is swapped in on its own.
    partial = f"coalition/partials/event/{step}.html"
    return render(
        request,
        partial if request.method == "POST" else "coalition/event_funnel.html",
        {
            "step": step,
            "form": form or _STEP_FORMS[step](initial=request.POST.dict()),
            "carried": _carried(request.POST, step),
            "previous_step": _previous_step(step),
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
