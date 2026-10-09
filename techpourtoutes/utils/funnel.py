from datetime import datetime, timedelta

from django.utils import timezone

# Fields that steer the funnel: they are never stored as answers.
_CONTROL_FIELDS = ("action", "csrfmiddlewaretoken")

# Bounds how long an abandoned funnel keeps its answers, the session itself living for months.
_TTL = timedelta(hours=1)


class FunnelSteps:
    """The ordered screens of a funnel. `optional` maps a screen to the answer that shows it:
    the screen is part of the funnel only while that answer is true."""

    def __init__(self, steps, optional=None):
        self.steps = steps
        self.optional = optional or {}

    @property
    def first(self):
        return self.steps[0]

    def active(self, answers):
        return [
            step
            for step in self.steps
            if step not in self.optional or answers.get(self.optional[step])
        ]

    def next(self, step, answers):
        """The first active screen following `step`, which may itself no longer be active; None
        once the last one is answered."""
        following = self.steps[self.steps.index(step) + 1 :]
        return next((other for other in following if other in self.active(answers)), None)

    def previous(self, step, answers):
        steps = self.active(answers)
        if step not in steps:
            return steps[0]
        return steps[max(steps.index(step) - 1, 0)]

    def missing_before(self, step, answered, answers):
        """The first active screen preceding `step` among those not `answered`, if any."""
        earlier = self.steps[: self.steps.index(step)]
        return next(
            (
                other
                for other in self.active(answers)
                if other in earlier and other not in answered
            ),
            None,
        )

    def last(self, answers):
        return self.active(answers)[-1]

    # The first screen carries no bar, so it takes no share. The "+ 1" reserves a final segment
    # for the success screen, which shows none either, so the last step stops short of 100%.
    def progress(self, step, answers):
        steps = self.active(answers)[1:]
        if step not in steps:
            return None
        return round(100 * (steps.index(step) + 1) / (len(steps) + 1))


class FunnelSession:
    """The answers of a funnel in progress, kept in the visitor's session under `key`."""

    def __init__(self, request, key):
        self.session = request.session
        self.key = key

    @property
    def answers(self):
        state = self._state()
        return _merged(state["values"], state["steps"])

    def answers_with(self, step, data):
        """The answers as they would be once `step` is replaced by `data`, without saving them."""
        state = self._state()
        return _merged(state["values"], {**state["steps"], step: _answers_in(data)})

    @property
    def answered(self):
        return set(self._state()["steps"])

    @property
    def current_step(self):
        return self._state()["current"]

    @current_step.setter
    def current_step(self, step):
        self._write(current=step)

    def save_step(self, step, data):
        self._write(steps={**self._state()["steps"], step: _answers_in(data)})

    def update(self, **values):
        self._write(values={**self._state()["values"], **values})

    def clear(self):
        self.session.pop(self.key, None)

    def _state(self):
        state = self.session.get(self.key)
        if state is None or _expired(state):
            self.clear()
            return {"current": None, "steps": {}, "values": {}}
        return state

    # The session only notices a write to one of its own keys, so the state is reassigned whole.
    def _write(self, **changes):
        self.session[self.key] = {
            **self._state(),
            **changes,
            "updated_at": timezone.now().isoformat(),
        }


def _answers_in(data):
    return {name: value for name, value in data.items() if name not in _CONTROL_FIELDS}


def _merged(values, steps):
    merged = dict(values)
    for answers in steps.values():
        merged.update(answers)
    return merged


def _expired(state):
    return timezone.now() - datetime.fromisoformat(state["updated_at"]) > _TTL
